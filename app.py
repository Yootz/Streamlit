from io import BytesIO
import re

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="AAR Weather Analysis", layout="wide")
st.title("AAR Weather Analysis Dashboard")

LOCATION_COLUMNS = [
	("Region", ["REGION"]),
	("Estate", ["ESTATE_NAME"]),
	("Divisi", ["DIVISION_NAME"]),
]

METRIC_SECTIONS = [
	(
		"Suhu dan Kelembapan Udara",
		[
			("Suhu rata-rata", ["TEMP_MEAN"], "°C", "mean"),
			("Suhu minimum", ["TEMP_MIN"], "°C", "mean"),
			("Suhu maksimum", ["TEMP_MAX"], "°C", "mean"),
			("Kelembapan relatif", ["RH", "RELATIVE_HUMIDITY", "HUMIDITY"], "%", "mean"),
			("Rentang suhu harian", ["DIURNAL"], "°C", "mean"),
			("Titik embun", ["DEW", "DEW_POINT"], "°C", "mean"),
		],
	),
	(
		"Tekanan Udara",
		[
			(
				"Tekanan udara",
				["PRESSURE", "AIR_PRESSURE", "ATM_PRESSURE", "ATMOSPHERIC_PRESSURE", "BAROMETRIC_PRESSURE", "PRES", "TEKANAN_UDARA"],
				"",
				"mean",
			),
		],
	),
	(
		"Kecepatan dan Arah Angin",
		[
			("Kecepatan angin", ["WIND_SPEED", "WINDSPEED"], "", "mean"),
			("Hembusan angin maksimum", ["WIND_GUST", "WINDGUST"], "", "mean"),
			(
				"Arah angin",
				["WIND_DIRECTION", "WIND_DIR", "WIND_DIRECTION_DEG", "WIND_DIRECTION_DEGREES", "WDIR", "ARAH_ANGIN"],
				"",
				"direction",
			),
		],
	),
	(
		"Curah Hujan",
		[
			("Curah hujan", ["RAINFALL", "PRECIPITATION"], "mm", "sum"),
			("Jumlah hari hujan", ["RAINDAY", "RAIN_DAYS"], "hari", "sum"),
		],
	),
	(
		"Radiasi Matahari dan Indeks UV",
		[
			("Radiasi matahari", ["SOLAR_RAD", "SOLAR_RADIATION", "SOLARRAD"], "", "mean"),
			("Indeks UV", ["UV_INDEX", "INDEX_UV", "UVI", "UV"], "", "mean"),
		],
	),
]


def normalize_name(value):
	return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def find_column(dataframe, aliases):
	normalized_columns = {normalize_name(column): column for column in dataframe.columns}
	for alias in aliases:
		column = normalized_columns.get(normalize_name(alias))
		if column is not None:
			return column
	return None


@st.cache_data(show_spinner="Membaca dataset...")
def read_dataset(file_bytes, extension):
	file_buffer = BytesIO(file_bytes)
	if extension == ".csv":
		return pd.read_csv(file_buffer)
	if extension == ".xlsx":
		return pd.read_excel(file_buffer)
	raise ValueError("Format file tidak didukung. Gunakan CSV atau XLSX.")


def clean_dataset(dataframe):
	cleaned = dataframe.copy()
	cleaned.columns = [str(column).strip() for column in cleaned.columns]

	for column in cleaned.select_dtypes(include=["object", "string"]).columns:
		values = cleaned[column].astype("string").str.strip()
		cleaned[column] = values.mask(values.eq(""), pd.NA)

	date_column = find_column(cleaned, ["DATE_RECORD", "DATE", "RECORD_DATE"])
	if date_column:
		cleaned[date_column] = pd.to_datetime(cleaned[date_column], errors="coerce")

	metric_columns = {}
	for _, metrics in METRIC_SECTIONS:
		for label, aliases, unit, aggregation in metrics:
			column = find_column(cleaned, aliases)
			if column is None:
				continue

			metric_columns[label] = column
			if aggregation != "direction":
				values = cleaned[column].astype("string").str.strip()
				values = values.str.replace(r"(?<=\d),(?=\d{3}(\D|$))", "", regex=True)
				cleaned[column] = pd.to_numeric(values, errors="coerce")

	location_columns = {}
	for label, aliases in LOCATION_COLUMNS:
		column = find_column(cleaned, aliases)
		if column is not None:
			cleaned[column] = cleaned[column].astype("string").fillna("Tidak diketahui")
			location_columns[label] = column

	return cleaned, date_column, metric_columns, location_columns


def direction_sector(value):
	if pd.isna(value):
		return pd.NA

	sectors = ["Utara", "Timur Laut", "Timur", "Tenggara", "Selatan", "Barat Daya", "Barat", "Barat Laut"]
	text = str(value).strip().upper()
	aliases = {
		"N": "Utara", "NORTH": "Utara", "NE": "Timur Laut", "ENE": "Timur Laut", "NNE": "Timur Laut",
		"E": "Timur", "EAST": "Timur", "SE": "Tenggara", "ESE": "Tenggara", "SSE": "Tenggara",
		"S": "Selatan", "SOUTH": "Selatan", "SW": "Barat Daya", "WSW": "Barat Daya", "SSW": "Barat Daya",
		"W": "Barat", "WEST": "Barat", "NW": "Barat Laut", "WNW": "Barat Laut", "NNW": "Barat Laut",
	}
	if text in aliases:
		return aliases[text]

	try:
		degrees = float(text) % 360
	except ValueError:
		return text.title()

	sector_index = int((degrees + 22.5) // 45) % len(sectors)
	return sectors[sector_index]


def make_metric_chart(dataframe, date_column, location_column, show_all_locations, metric_column, label, unit, aggregation):
	chart_data = dataframe.copy()
	group_column = location_column if show_all_locations else None

	if group_column:
		top_locations = chart_data[group_column].value_counts().head(10).index
		chart_data = chart_data[chart_data[group_column].isin(top_locations)]

	if aggregation == "direction":
		chart_data["Arah"] = chart_data[metric_column].map(direction_sector)
		grouping = ["Arah"] + ([group_column] if group_column else [])
		grouped = chart_data.groupby(grouping, dropna=True).size().reset_index(name="Jumlah pengamatan")
		direction_order = ["Utara", "Timur Laut", "Timur", "Tenggara", "Selatan", "Barat Daya", "Barat", "Barat Laut"]
		order = [direction for direction in direction_order if direction in grouped["Arah"].values]
		figure = px.bar(
			grouped,
			x="Arah",
			y="Jumlah pengamatan",
			color=group_column,
			category_orders={"Arah": order},
			title=f"Distribusi {label.lower()}",
		)
		return figure

	operation = "sum" if aggregation == "sum" else "mean"
	if date_column and chart_data[date_column].notna().any():
		group_columns = [date_column] + ([group_column] if group_column else [])
		grouped = chart_data.dropna(subset=[date_column]).groupby(group_columns, dropna=False)[metric_column].agg(operation).reset_index()
		figure = px.line(
			grouped,
			x=date_column,
			y=metric_column,
			color=group_column,
			markers=True,
			title=f"Tren {label.lower()}",
			labels={metric_column: f"{label} ({unit})" if unit else label, date_column: "Tanggal"},
		)
		return figure

	if group_column:
		grouped = chart_data.groupby(group_column, dropna=False)[metric_column].agg(operation).reset_index()
		return px.bar(
			grouped,
			x=group_column,
			y=metric_column,
			title=f"{label} berdasarkan lokasi",
			labels={metric_column: f"{label} ({unit})" if unit else label, group_column: location_column},
		)

	return px.histogram(chart_data, x=metric_column, title=f"Sebaran {label.lower()}")


uploaded_file = st.file_uploader("Unggah dataset CSV atau Excel", type=["csv", "xlsx"])
if uploaded_file is None:
	st.info("Unggah dataset dengan kolom sesuai columns_name.md untuk memulai analisis.")
	st.stop()

try:
	extension = "." + uploaded_file.name.rsplit(".", 1)[-1].lower()
	source_df = read_dataset(uploaded_file.getvalue(), extension)
except Exception as error:
	st.error(f"File tidak dapat dibaca: {error}")
	st.stop()

if source_df.empty or len(source_df.columns) == 0:
	st.error("File tidak berisi data yang dapat dianalisis.")
	st.stop()

df, date_column, metric_columns, location_columns = clean_dataset(source_df)
if not location_columns:
	st.error("Kolom lokasi tidak ditemukan. Dataset perlu memiliki REGION, ESTATE_NAME, atau DIVISION_NAME.")
	st.stop()

filter_col, value_col = st.columns(2)
with filter_col:
	selected_level = st.selectbox("Kelompok lokasi", list(location_columns))

location_column = location_columns[selected_level]
location_values = sorted(df[location_column].dropna().astype(str).unique().tolist())
with value_col:
	selected_location = st.selectbox("Pilih lokasi", ["Semua", *location_values])

show_all_locations = selected_location == "Semua"
analysis_df = df if show_all_locations else df[df[location_column].astype(str) == selected_location]
if analysis_df.empty:
	st.warning("Tidak ada data untuk pilihan lokasi ini.")
	st.stop()

st.caption(f"Analisis berdasarkan {selected_level.lower()}: {selected_location} | {len(analysis_df):,} baris")

available_metrics = {label: column for label, column in metric_columns.items()}
summary_specs = [
	("Suhu rata-rata", "Suhu rata-rata", "°C", "mean"),
	("Kelembapan", "Kelembapan relatif", "%", "mean"),
	("Curah hujan", "Curah hujan", "mm", "sum"),
	("Radiasi matahari", "Radiasi matahari", "", "mean"),
]
summary_items = []
for title, metric_label, unit, operation in summary_specs:
	column = available_metrics.get(metric_label)
	if column is None:
		continue
	values = analysis_df[column].dropna()
	if values.empty:
		continue
	result = values.sum() if operation == "sum" else values.mean()
	formatted = f"{result:,.1f}{f' {unit}' if unit else ''}"
	summary_items.append((title, formatted))

if summary_items:
	summary_columns = st.columns(len(summary_items))
	for column, (title, value) in zip(summary_columns, summary_items):
		column.metric(title, value)

tabs = st.tabs([section[0] for section in METRIC_SECTIONS])
for tab, (section_title, metrics) in zip(tabs, METRIC_SECTIONS):
	with tab:
		section_available = [metric for metric in metrics if metric[0] in available_metrics]
		section_missing = [metric[0] for metric in metrics if metric[0] not in available_metrics]

		if not section_available:
			st.info(f"Kolom untuk analisis {section_title.lower()} tidak ditemukan pada dataset.")
			continue

		if section_missing:
			st.caption("Data opsional yang tidak tersedia: " + ", ".join(section_missing))

		chart_columns = st.columns(2)
		for index, (label, aliases, unit, aggregation) in enumerate(section_available):
			metric_column = available_metrics[label]
			chart_data = analysis_df.dropna(subset=[metric_column])
			if chart_data.empty:
				with chart_columns[index % 2]:
					st.info(f"Kolom {label.lower()} tidak memiliki nilai valid.")
				continue

			figure = make_metric_chart(
				chart_data,
				date_column,
				location_column,
				show_all_locations,
				metric_column,
				label,
				unit,
				aggregation,
			)
			figure.update_layout(legend_title_text=selected_level)
			with chart_columns[index % 2]:
				st.plotly_chart(figure, width="stretch")
				if show_all_locations and chart_data[location_column].nunique() > 10:
					st.caption("Grafik dibatasi ke 10 lokasi dengan jumlah pengamatan terbanyak.")

with st.expander("Pratinjau dataset"):
	st.dataframe(analysis_df, width="stretch")
