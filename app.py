import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide", page_title="India Rural Literacy Dashboard")

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    df = pd.read_csv("RS_Session_266_AU_997_A_to_C_1.csv")
    df.columns = df.columns.str.strip()
    
    with open("india.geojson") as f:
        india_geo = json.load(f)
    
    # Standardize CSV Name and handle Uttarakhand fix
    df['State/UT'] = df['State/UT'].str.strip().replace({'Uttaranchal': 'Uttarakhand'})
    df['MAP_MATCH'] = df['State/UT'].str.upper() 
    
    for col in ['2023-24', '2022-23', '2021-22']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    for feature in india_geo['features']:
        name = (feature['properties'].get('ST_NM') or 
                feature['properties'].get('NAME_1') or 
                feature['properties'].get('state_name') or "")
        original_name = str(name).strip().upper()
        
        # Brute force Uttarakhand matching
        if original_name.startswith("UTTAR") and "PRADESH" not in original_name:
            final_id = "UTTARAKHAND"
        else:
            final_id = original_name
            
        feature['properties']['JOIN_ID'] = final_id
        
    return df, india_geo

try:
    df, india_geo = load_data()
    all_regions = sorted(df['State/UT'].unique().tolist())
    
    # Initialize session states
    if 'current_selection' not in st.session_state:
        st.session_state.current_selection = "All India"

    # --- 3. SIDEBAR ---
    with st.sidebar:
        st.title("🕹️ Controls")
        selected_year = st.selectbox("Select Academic Year", ['2023-24', '2022-23', '2021-22'])
        
        # FIXED RESET BUTTON: Clears selection and resets view
        if st.button("🔄 Reset Map & View"):
            st.session_state.current_selection = "All India"
            st.rerun()
      
        dropdown_val = st.selectbox("Select State/UT", ["All India"] + all_regions,
            index=0 if st.session_state.current_selection == "All India" else all_regions.index(st.session_state.current_selection) + 1)
      
        if dropdown_val != st.session_state.current_selection:
            st.session_state.current_selection = dropdown_val
            st.rerun()

        st.divider()
        st.subheader(f"🏆 Top 5 ({selected_year})")
        top_5 = df.sort_values(by=selected_year, ascending=False).head(5)
        for i, (idx, row) in enumerate(top_5.iterrows(), 1):
            st.markdown(f"{i}. **{row['State/UT']}:** :green-background[{row[selected_year]:.1f}%]")

    # --- 4. MAIN INTERFACE ---
    st.title("📍 Rural Literacy Rates Across Indian States (2021-2024)")
  
    # --- 5. THE MAP ---
    fig_map = px.choropleth(
        df, geojson=india_geo, featureidkey="properties.JOIN_ID",
        locations="MAP_MATCH", color=selected_year,
        color_continuous_scale="RdYlGn", template="plotly_dark",
        hover_name="State/UT"
    )

    fig_map.update_traces(
        marker_line_color='white',
        marker_line_width=1.0,
        hovertemplate="<b>%{hovertext}</b><br>Rate: %{z}%<extra></extra>"
    )

    # FIXED RESET POSITION: fitbounds="locations" ensures it snaps back to full India
    fig_map.update_geos(
        visible=False, 
        fitbounds="locations", 
        bgcolor="black",
        projection_type='mercator'
    )
  
    fig_map.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0}, height=650,
        paper_bgcolor='black', plot_bgcolor='black',
        coloraxis_colorbar=dict(orientation='h', y=-0.1, x=0.5, xanchor='center', title=None),
        clickmode='event+select', dragmode=False
    )

    # Highlight Selection logic
    if st.session_state.current_selection != "All India":
        match_val = df[df['State/UT'] == st.session_state.current_selection]['MAP_MATCH'].values[0]
        state_idx = df[df['MAP_MATCH'] == match_val].index.tolist()
        fig_map.update_traces(selectedpoints=state_idx, unselected={'marker': {'opacity': 0.3}})

    # Capture map clicks
    map_selection = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun", config={'displayModeBar': False})

    if map_selection and "selection" in map_selection and map_selection["selection"]["points"]:
        clicked_state = map_selection["selection"]["points"][0]["hovertext"]
        if clicked_state != st.session_state.current_selection:
            st.session_state.current_selection = clicked_state
            st.rerun()

    # --- 6. FIXED DYNAMIC TREND CHART ---
    # This section now explicitly checks if a state is selected
    if st.session_state.current_selection != "All India":
        st.divider()
        st.subheader(f"📈 3-Year Trend: {st.session_state.current_selection}")
        
        state_data = df[df['State/UT'] == st.session_state.current_selection]
        
        if not state_data.empty:
            # We melt the 3 years for the bar chart
            trend_data = pd.melt(
                state_data, 
                id_vars=['State/UT'], 
                value_vars=['2021-22', '2022-23', '2023-24'],
                var_name='Year', 
                value_name='Rate'
            )
            
            fig_trend = px.bar(
                trend_data, x='Year', y='Rate', 
                text_auto='.1f', color='Rate', 
                color_continuous_scale="RdYlGn",
                range_y=[0, 105]
            )
            
            fig_trend.update_layout(
                height=400, template="plotly_dark", 
                paper_bgcolor='black', plot_bgcolor='black',
                xaxis_title="Academic Year", yaxis_title="Literacy Rate (%)"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("Data not found for the selected state.")

except Exception as e:
    st.error(f"Dashboard Error: {e}")