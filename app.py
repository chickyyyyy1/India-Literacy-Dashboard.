import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide", page_title="India Rural Literacy Dashboard")

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    # Load CSV
    df = pd.read_csv("RS_Session_266_AU_997_A_to_C_1.csv")
    df.columns = df.columns.str.strip() #
    
    # Load GeoJSON
    with open("india.geojson") as f:
        india_geo = json.load(f)
    
    # Standardize CSV Name
    df['State/UT'] = df['State/UT'].str.strip() #
    # Force "Uttaranchal" to "Uttarakhand" in CSV
    df['State/UT'] = df['State/UT'].replace({'Uttaranchal': 'Uttarakhand'})
    df['MAP_MATCH'] = df['State/UT'].str.upper() 
    
    for col in ['2023-24', '2022-23', '2021-22']:
        df[col] = pd.to_numeric(df[col], errors='coerce') #
        
    # --- THE BRUTE FORCE MAP FIX ---
    for feature in india_geo['features']:
        # Extract any possible name from the GeoJSON
        name = (feature['properties'].get('ST_NM') or 
                feature['properties'].get('NAME_1') or 
                feature['properties'].get('state_name') or "")
        
        original_name = str(name).strip().upper()
        
        # FIX: If the name starts with "UTTAR" (catches Uttaranchal/Uttarakhand/Uttarkand), 
        # force it to UTTARAKHAND to match our CSV
        if original_name.startswith("UTTAR") and "PRADESH" not in original_name:
            final_id = "UTTARAKHAND"
        else:
            final_id = original_name
            
        feature['properties']['JOIN_ID'] = final_id
        
    return df, india_geo

try:
    df, india_geo = load_data()
    all_regions = sorted(df['State/UT'].unique().tolist())
    
    if 'current_selection' not in st.session_state:
        st.session_state.current_selection = "All India"

    # --- 3. SIDEBAR ---
    with st.sidebar:
        st.title("🕹️ Controls")
        selected_year = st.selectbox("Select Academic Year", ['2023-24', '2022-23', '2021-22']) #
        
        if st.button("🔄 Reset Map"):
            st.session_state.current_selection = "All India"
            st.rerun() #
      
        dropdown_val = st.selectbox("Select State/UT", ["All India"] + all_regions,
            index=0 if st.session_state.current_selection == "All India" else all_regions.index(st.session_state.current_selection) + 1)
      
        if dropdown_val != st.session_state.current_selection:
            st.session_state.current_selection = dropdown_val
            st.rerun() #

        st.divider()
        st.subheader(f"🏆 Top 5 ({selected_year})")
        top_5 = df.sort_values(by=selected_year, ascending=False).head(5) #
        for i, (idx, row) in enumerate(top_5.iterrows(), 1):
            st.markdown(f"{i}. **{row['State/UT']}:** :green-background[{row[selected_year]:.1f}%]")

    # --- 4. MAIN INTERFACE ---
    st.title("📍 Rural Literacy Rates Across Indian States (2021-2024)")
  
    # --- 5. THE MAP ---
    fig_map = px.choropleth(
        df, geojson=india_geo, featureidkey="properties.JOIN_ID",
        locations="MAP_MATCH", color=selected_year,
        color_continuous_scale="RdYlGn", template="plotly_dark",
        hover_name="State/UT" #
    )

    fig_map.update_traces(
        marker_line_color='white',
        marker_line_width=1.5,
        hovertemplate="<b>%{hovertext}</b><br>Rate: %{z}%<extra></extra>"
    )

    fig_map.update_geos(visible=False, fitbounds="locations", bgcolor="black") #
  
    fig_map.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0}, height=650,
        paper_bgcolor='black', plot_bgcolor='black',
        coloraxis_colorbar=dict(orientation='h', y=-0.15, x=0.5, xanchor='center', title=None),
        clickmode='event+select', dragmode=False #
    )

    # Highlight Selection
    if st.session_state.current_selection != "All India":
        match_val = df[df['State/UT'] == st.session_state.current_selection]['MAP_MATCH'].values[0]
        state_idx = df[df['MAP_MATCH'] == match_val].index.tolist()
        fig_map.update_traces(selectedpoints=state_idx, unselected={'marker': {'opacity': 0.3}})

    # Reruns on select for instant response
    map_selection = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun", config={'displayModeBar': False})

    if map_selection and "selection" in map_selection and map_selection["selection"]["points"]:
        clicked_state = map_selection["selection"]["points"][0]["hovertext"]
        if clicked_state != st.session_state.current_selection:
            st.session_state.current_selection = clicked_state
            st.rerun()

except Exception as e:
    st.error(f"Dashboard Error: {e}")