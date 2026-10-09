import plotly.express as px
import pandas as pd
import streamlit as st
import openpyxl


st.title("AAR Data Analysis Dashboard")


def clean_dataframe(dataframe):
    """Normalize blanks and infer common numeric/date columns conservatively."""
    cleaned = dataframe.copy()
    cleaned.columns = [str(column).strip() or f"Kolom {index + 1}" for index, column in enumerate(cleaned.columns)]
    cleaned = cleaned.replace(r"^\s*$", pd.NA, regex=True)
    cleaned = cleaned.replace([float("inf"), float("-inf")], pd.NA)
    converted_columns = []

    for column in cleaned.columns:
        series = cleaned[column]
        if pd.api.types.is_numeric_dtype(series):
            continue

        non_missing = series.dropna()
        if non_missing.empty:
            continue

        text = series.astype("string").str.strip()
        numeric_text = text.str.replace(r"(?<=\d),(?=\d{3}(\D|$))", "", regex=True)
        numeric_values = pd.to_numeric(numeric_text, errors="coerce")
        numeric_ratio = numeric_values.notna().sum() / len(non_missing)

        if numeric_ratio >= 0.8:
            cleaned[column] = numeric_values
            converted_columns.append(column)
            continue

        has_date_markers = text.str.contains(r"[-/:]", na=False).any()
        if has_date_markers:
            date_values = pd.to_datetime(series, errors="coerce")
            date_ratio = date_values.notna().sum() / len(non_missing)
            if date_ratio >= 0.8:
                cleaned[column] = date_values
                converted_columns.append(column)
                continue

        cleaned[column] = text

    empty_counts = cleaned.isna().sum()
    categorical_columns = cleaned.select_dtypes(include=["object", "string", "category"]).columns
    for column in categorical_columns:
        if empty_counts[column] < len(cleaned):
            cleaned[column] = cleaned[column].fillna("Tidak diketahui")

    return cleaned, converted_columns, empty_counts


# Load the dataset
uploaded_file = st.file_uploader("Choose a file from your computer", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            source_df = pd.read_csv(uploaded_file)
        else:
            source_df = pd.read_excel(uploaded_file)
        source_df.to_parquet("data.parquet", index=False)
        source_df = pd.read_parquet("data.parquet")
    except Exception as error:
        st.error(f"File tidak dapat dibaca: {error}")
        st.stop()

    if source_df.empty or len(source_df.columns) == 0:
        st.error("File tidak berisi data yang dapat dianalisis.")
        st.stop()

    df, converted_columns, missing_counts = clean_dataframe(source_df)
    usable_columns = [column for column in df.columns if df[column].notna().any()]
    if not usable_columns:
        st.error("Tidak ada kolom dengan data yang dapat divisualisasikan.")
        st.stop()

    numeric_columns = [
        column for column in usable_columns
        if pd.api.types.is_numeric_dtype(df[column])
    ]
    date_columns = [
        column for column in usable_columns
        if pd.api.types.is_datetime64_any_dtype(df[column])
    ]
    categorical_columns = [
        column for column in usable_columns
        if column not in numeric_columns and column not in date_columns
    ]

    if date_columns and numeric_columns:
        recommended_chart = "Garis"
    elif categorical_columns and numeric_columns:
        recommended_chart = "Batang"
    elif len(numeric_columns) >= 2:
        recommended_chart = "Sebar"
    elif numeric_columns:
        recommended_chart = "Histogram"
    else:
        recommended_chart = "Batang"

    chart_options = ["Batang", "Garis"]
    if numeric_columns:
        chart_options.append("Histogram")
        chart_options.append("Kotak")
    if len(numeric_columns) >= 2:
        chart_options.append("Sebar")
    if numeric_columns and categorical_columns:
        chart_options.append("Pie")

    st.subheader("Visualisasi")
    if converted_columns:
        st.caption("Kolom yang tipe datanya diperbaiki: " + ", ".join(converted_columns))

    with st.expander("Ringkasan nilai kosong"):
        missing_summary = missing_counts[missing_counts > 0].rename("Jumlah kosong")
        if missing_summary.empty:
            st.write("Tidak ada nilai kosong yang terdeteksi.")
        else:
            st.dataframe(missing_summary.to_frame(), use_container_width=True)
            st.caption("Nilai kosong pada kolom kategori ditampilkan sebagai 'Tidak diketahui'.")

    selected_chart = st.selectbox(
        "Jenis grafik",
        chart_options,
        index=chart_options.index(recommended_chart),
    )

    if selected_chart in ("Histogram", "Sebar"):
        x_options = numeric_columns
    else:
        x_options = usable_columns

    if selected_chart == "Histogram":
        x_default = numeric_columns[0]
    elif selected_chart == "Sebar" and len(numeric_columns) > 1:
        x_default = numeric_columns[0]
    elif date_columns and selected_chart == "Garis":
        x_default = date_columns[0]
    elif categorical_columns:
        x_default = categorical_columns[0]
    else:
        x_default = usable_columns[0]

    x_column = st.selectbox("Sumbu X", x_options, index=x_options.index(x_default))
    color_options = ["Tanpa warna tambahan", *categorical_columns]
    color_selection = st.selectbox("Warna / kelompok", color_options)
    color_column = None if color_selection == "Tanpa warna tambahan" else color_selection

    y_column = None
    aggregation = "Tidak ada"
    if selected_chart != "Histogram":
        y_options = list(numeric_columns)
        if selected_chart in ("Batang", "Garis", "Pie"):
            y_options.insert(0, "Hitung jumlah baris")
        default_y = numeric_columns[0] if numeric_columns else "Hitung jumlah baris"
        y_column = st.selectbox("Sumbu Y", y_options, index=y_options.index(default_y))

        if selected_chart in ("Batang", "Garis") and y_column != "Hitung jumlah baris":
            aggregation = st.selectbox("Agregasi", ["Rata-rata", "Total", "Tidak ada"])

    plot_df = df.copy()
    required_columns = [x_column]
    if y_column and y_column != "Hitung jumlah baris":
        required_columns.append(y_column)
    if color_column:
        required_columns.append(color_column)

    rows_before_filter = len(plot_df)
    plot_df = plot_df.dropna(subset=required_columns)
    dropped_rows = rows_before_filter - len(plot_df)
    if dropped_rows:
        st.caption(f"{dropped_rows} baris dengan nilai kosong pada kolom grafik dikeluarkan.")

    if plot_df.empty:
        st.warning("Tidak ada baris yang cukup lengkap untuk membuat grafik dengan pilihan ini.")
        st.stop()

    color_argument = {"color": color_column} if color_column else {}
    if selected_chart == "Histogram":
        figure = px.histogram(plot_df, x=x_column, **color_argument)
    elif y_column == "Hitung jumlah baris":
        grouping_columns = [x_column]
        if color_column and selected_chart != "Pie":
            grouping_columns.append(color_column)
        grouped = plot_df.groupby(grouping_columns, dropna=False).size().reset_index(name="Jumlah baris")
        if selected_chart == "Pie":
            figure = px.pie(grouped, names=x_column, values="Jumlah baris")
        elif selected_chart == "Garis":
            figure = px.line(
                grouped,
                x=x_column,
                y="Jumlah baris",
                **({"color": color_column} if color_column else {}),
            )
        else:
            figure = px.bar(grouped, x=x_column, y="Jumlah baris", **({"color": color_column} if color_column else {}))
    elif selected_chart in ("Batang", "Garis") and aggregation != "Tidak ada":
        operation = "mean" if aggregation == "Rata-rata" else "sum"
        grouped = plot_df.groupby(x_column, dropna=False)[y_column].agg(operation).reset_index()
        if color_column:
            grouped = plot_df.groupby([x_column, color_column], dropna=False)[y_column].agg(operation).reset_index()
        if selected_chart == "Garis":
            figure = px.line(grouped, x=x_column, y=y_column, **({"color": color_column} if color_column else {}))
        else:
            figure = px.bar(grouped, x=x_column, y=y_column, **({"color": color_column} if color_column else {}))
    elif selected_chart == "Sebar":
        figure = px.scatter(plot_df, x=x_column, y=y_column, **color_argument)
    elif selected_chart == "Kotak":
        figure = px.box(plot_df, x=x_column, y=y_column, **color_argument)
    elif selected_chart == "Pie":
        figure = px.pie(plot_df, names=x_column, values=y_column)
    else:
        figure = px.bar(plot_df, x=x_column, y=y_column, **color_argument)

    st.plotly_chart(figure, use_container_width=True)
    with st.expander("Pratinjau data yang sudah dibersihkan"):
        st.dataframe(df, use_container_width=True)
else:
    st.warning("Please upload a CSV or Excel file to proceed.")
    st.stop()


