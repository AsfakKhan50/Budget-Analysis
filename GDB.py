import streamlit as st
import pandas as pd
import altair as alt

# ---------- APP CONFIG ----------
st.set_page_config(
    page_title="India Budget – Department Analysis",
    page_icon="📊",
    layout="wide"
)

# ---------- HELPER FUNCTIONS ----------
@st.cache_data
def load_data(path_or_file):
    df = pd.read_csv(path_or_file)
    # Ensure first column is Department, rest are years
    df.rename(columns={df.columns[0]: "Department"}, inplace=True)
    # Keep only numeric year columns
    year_cols = [c for c in df.columns if c != "Department"]
    # Melt into long format: Department | Year | Budget
    long_df = df.melt(id_vars="Department",
                      value_vars=year_cols,
                      var_name="Year",
                      value_name="Budget")
    long_df["Year"] = long_df["Year"].astype(str)
    long_df["Budget"] = pd.to_numeric(long_df["Budget"], errors="coerce")
    long_df.dropna(subset=["Budget"], inplace=True)
    return df, long_df, year_cols


def compute_growth(row, year_cols):
    """Compute simple growth metrics for a department."""
    values = row[year_cols].values.astype(float)
    start = values[0]
    end = values[-1]
    absolute_change = end - start
    pct_change = (absolute_change / start * 100) if start != 0 else None
    return start, end, absolute_change, pct_change


# ---------- SIDEBAR: DATA INPUT ----------
st.sidebar.title("⚙️ Controls")

st.sidebar.markdown(
    "Upload your **Department_Budget_2014_to_2025.csv** file "
    "or use the default path."
)

uploaded = st.sidebar.file_uploader(
    "Upload CSV", type=["csv"], help="Columns: Department, 2014, 2015, ... 2025"
)

default_path = "Department_Budget_2014_to_2025.csv"

if uploaded is not None:
    df, long_df, year_cols = load_data(uploaded)
else:
    df, long_df, year_cols = load_data(default_path)

min_year, max_year = min(year_cols), max(year_cols)

year_range = st.sidebar.slider(
    "Select Year Range",
    min_value=int(min_year),
    max_value=int(max_year),
    value=(int(min_year), int(max_year)),
    step=1
)

# filter by selected years
selected_years = [str(y) for y in range(year_range[0], year_range[1] + 1)]
filtered_long = long_df[long_df["Year"].isin(selected_years)]

st.sidebar.markdown("---")
st.sidebar.markdown("Made from your **PySpark budget project** and extended with:")
st.sidebar.markdown(
"- Interactive filters\n"
"- Department comparison\n"
"- Growth analytics\n"
"- Download options"
)

# ---------- MAIN TITLE ----------
st.title("📊 Real-Time Budget Analysis of Government of India Departments")

st.caption(
    "Interactive dashboard built with Streamlit · Data: Department-wise budget "
    "allocations (₹ Crores), 2014–2025."
)

# ---------- TABS ----------
tab_overview, tab_dept, tab_compare, tab_info = st.tabs(
    ["📈 Overview", "🏛 Department Analysis", "⚖️ Comparison", "ℹ️ About Budget"]
)

# ---------- OVERVIEW TAB ----------
with tab_overview:
    st.subheader("Overall Budget Trends")

    # total budget per year
    total_by_year = (
        filtered_long.groupby("Year", as_index=False)["Budget"].sum()
        .sort_values("Year")
    )

    col1, col2, col3, col4 = st.columns(4)

    total_budget_latest = total_by_year[total_by_year["Year"] == max(selected_years)]["Budget"].iloc[0]
    total_budget_first = total_by_year[total_by_year["Year"] == min(selected_years)]["Budget"].iloc[0]
    abs_change = total_budget_latest - total_budget_first
    pct_change = abs_change / total_budget_first * 100 if total_budget_first != 0 else 0

    col1.metric("First Year Total Budget (₹ Cr)", f"{total_budget_first:,.0f}")
    col2.metric("Latest Year Total Budget (₹ Cr)", f"{total_budget_latest:,.0f}",
                f"{abs_change:,.0f}")
    col3.metric("Growth (%)", f"{pct_change:,.1f}%")
    col4.metric("No. of Departments", filtered_long["Department"].nunique())

    st.markdown("### Total Budget by Year")
    line = (
        alt.Chart(total_by_year)
        .mark_line(point=True)
        .encode(
            x="Year:O",
            y=alt.Y("Budget:Q", title="Budget (₹ Crores)"),
            tooltip=["Year", alt.Tooltip("Budget:Q", format=",.0f")],
        )
        .properties(height=350)
    )
    st.altair_chart(line, use_container_width=True)

    st.markdown("### Top 5 Departments – Latest Year")
    latest_year_df = filtered_long[filtered_long["Year"] == max(selected_years)]
    top5 = (
        latest_year_df.groupby("Department", as_index=False)["Budget"]
        .sum()
        .sort_values("Budget", ascending=False)
        .head(5)
    )
    bar = (
        alt.Chart(top5)
        .mark_bar()
        .encode(
            x=alt.X("Budget:Q", title="Budget (₹ Crores)"),
            y=alt.Y("Department:N", sort="-x"),
            tooltip=["Department", alt.Tooltip("Budget:Q", format=",.0f")],
        )
        .properties(height=300)
    )
    st.altair_chart(bar, use_container_width=True)

    with st.expander("📥 Download current data (filtered years)"):
        st.download_button(
            label="Download CSV",
            data=filtered_long.to_csv(index=False).encode("utf-8"),
            file_name="filtered_budget_data.csv",
            mime="text/csv",
        )

# ---------- DEPARTMENT ANALYSIS TAB ----------
with tab_dept:
    st.subheader("Department-wise Budget Analysis")

    dept = st.selectbox(
        "Select Department",
        options=sorted(filtered_long["Department"].unique()),
    )

    dept_data_wide = df[df["Department"] == dept].copy()
    dept_long = filtered_long[filtered_long["Department"] == dept].copy()
    dept_long = dept_long.sort_values("Year")

    col_a, col_b = st.columns(2)
    st.markdown(f"### {dept}")

    # growth metrics using full year_cols (not only filtered)
    start, end, abs_change, pct_change = compute_growth(
        dept_data_wide.set_index("Department").loc[dept], year_cols
    )

    col_a.metric(
        "First Year Budget (₹ Cr)",
        f"{start:,.0f}"
    )
    col_b.metric(
        "Latest Year Budget (₹ Cr)",
        f"{end:,.0f}",
        f"{abs_change:,.0f} ({pct_change:,.1f}%)" if pct_change is not None else "N/A",
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Bar Chart")
        bar_dept = (
            alt.Chart(dept_long)
            .mark_bar()
            .encode(
                x="Year:O",
                y=alt.Y("Budget:Q", title="Budget (₹ Crores)"),
                tooltip=["Year", alt.Tooltip("Budget:Q", format=",.0f")],
            )
            .properties(height=350)
        )
        st.altair_chart(bar_dept, use_container_width=True)

    with c2:
        st.markdown("#### Line Chart")
        line_dept = (
            alt.Chart(dept_long)
            .mark_line(point=True)
            .encode(
                x="Year:O",
                y=alt.Y("Budget:Q", title="Budget (₹ Crores)"),
                tooltip=["Year", alt.Tooltip("Budget:Q", format=",.0f")],
            )
            .properties(height=350)
        )
        st.altair_chart(line_dept, use_container_width=True)

    st.markdown("#### Data Table")
    st.dataframe(
        dept_data_wide.set_index("Department").T.rename(columns={dept: "Budget (₹ Cr)"}),
        use_container_width=True,
    )

# ---------- COMPARISON TAB ----------
with tab_compare:
    st.subheader("Compare Multiple Departments")

    multi_depts = st.multiselect(
        "Select Departments to Compare",
        options=sorted(filtered_long["Department"].unique()),
        default=sorted(filtered_long["Department"].unique())[:3],
    )

    if multi_depts:
        compare_df = filtered_long[filtered_long["Department"].isin(multi_depts)]
        line_multi = (
            alt.Chart(compare_df)
            .mark_line(point=True)
            .encode(
                x="Year:O",
                y=alt.Y("Budget:Q", title="Budget (₹ Crores)"),
                color="Department:N",
                tooltip=["Department", "Year", alt.Tooltip("Budget:Q", format=",.0f")],
            )
            .properties(height=400)
        )
        st.altair_chart(line_multi, use_container_width=True)

        st.markdown("#### Summary Table (Latest Year)")
        latest = compare_df[compare_df["Year"] == max(selected_years)]
        latest_pivot = latest.pivot_table(
            index="Department", values="Budget", aggfunc="sum"
        ).sort_values("Budget", ascending=False)
        st.dataframe(latest_pivot, use_container_width=True)
    else:
        st.info("Select at least one department to see comparison.")

# ---------- ABOUT TAB ----------
with tab_info:
    st.subheader("Why the Union Budget Matters")

    st.markdown(
        """
From your original project, the key roles of the Government of India budget include: :contentReference[oaicite:1]{index=1}  

1. **Economic planning and stability** – guiding growth, controlling inflation, and maintaining financial stability.  
2. **Resource allocation** – distributing funds across sectors like agriculture, defence, education, and health.  
3. **Social welfare & development** – supporting schemes for poverty reduction, employment, and inclusive growth.  
4. **Infrastructure & investment** – funding public works and capital projects to boost economic activity.  
5. **Fiscal responsibility & transparency** – presenting clear revenue and expenditure data to ensure accountability.  

This app extends your PySpark + Matplotlib analysis into an **interactive Streamlit dashboard**  
where users can explore trends, compare departments, and download filtered data.
        """
    )

    st.markdown("#### Raw Data Preview")
    st.dataframe(df, use_container_width=True)
