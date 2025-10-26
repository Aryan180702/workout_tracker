"""
Multi-User Workout Tracker App - FINAL VERSION
Built with Streamlit, Streamlit-Authenticator, and Supabase
"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import datetime
import pandas as pd
from database import WorkoutDatabase
from collections import defaultdict

# ===== PAGE CONFIGURATION =====
st.set_page_config(
    page_title="Workout Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== LOAD CONFIGURATION =====
@st.cache_resource
def load_config():
    """Load authentication config from YAML file"""
    try:
        with open('workout_tracker/config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)
        return config
    except FileNotFoundError:
        st.error("❌ config.yaml not found! Please create it first.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading config.yaml: {e}")
        st.stop()

def save_config(config):
    """Save updated config back to YAML file"""
    try:
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file)
    except Exception as e:
        st.error(f"❌ Error saving config: {e}")

config = load_config()

# ===== CREATE AUTHENTICATOR =====
try:
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"❌ Authentication setup failed: {e}")
    st.stop()

# ===== INITIALIZE DATABASE =====
@st.cache_resource
def init_database():
    """Initialize database connection"""
    return WorkoutDatabase()

db = init_database()

# ===== PREDEFINED DATA =====
MUSCLE_GROUPS = [
    "Chest", "Back", "Shoulders", "Biceps", "Triceps", 
    "Legs", "Abs", "Glutes", "Calves", "Forearms"
]

EXERCISES = {
    "Chest": ["Bench Press", "Incline Bench Press", "Dumbbell Flyes", "Push-ups", "Cable Crossover"],
    "Back": ["Pull-ups", "Deadlift", "Barbell Row", "Lat Pulldown", "Seated Cable Row"],
    "Shoulders": ["Overhead Press", "Lateral Raises", "Front Raises", "Face Pulls", "Shrugs"],
    "Biceps": ["Barbell Curl", "Dumbbell Curl", "Hammer Curl", "Preacher Curl", "Cable Curl"],
    "Triceps": ["Tricep Dips", "Close-Grip Bench Press", "Skull Crushers", "Tricep Pushdown", "Overhead Extension"],
    "Legs": ["Squat", "Leg Press", "Lunges", "Leg Curl", "Leg Extension"],
    "Abs": ["Crunches", "Planks", "Russian Twists", "Leg Raises", "Cable Crunches"],
    "Glutes": ["Hip Thrust", "Bulgarian Split Squat", "Glute Bridge", "Cable Kickbacks", "Step-ups"],
    "Calves": ["Standing Calf Raise", "Seated Calf Raise", "Calf Press on Leg Press"],
    "Forearms": ["Wrist Curl", "Reverse Wrist Curl", "Farmer's Walk", "Dead Hang"]
}

tab1, tab2, tab3 = st.tabs(["🏋️ Login", "📝 Sign Up", "ℹ️ About"])

# ===== TAB 1: LOGIN =====
with tab1:
    st.title("💪 Workout Tracker - Login")
    
    authenticator.login(location='main')
    
    if st.session_state.get("authentication_status"):
        # ✅ USER IS LOGGED IN
        
        st.sidebar.success(f'✅ Welcome *{st.session_state["name"]}*')
        authenticator.logout(location='sidebar')
        
        # ===== SIDEBAR NAVIGATION =====
        st.sidebar.title("📱 Navigation")
        page = st.sidebar.radio(
            "Go to",
            ["Add Workout", "View History", "Statistics"],
            label_visibility="collapsed"
        )
        
        # ===== PAGE 1: ADD WORKOUT =====
        if page == "Add Workout":
            st.header("📝 Log Your Workout")
            
            # Get user's routines
            routines = db.get_user_routines(st.session_state['username'])
            
            # ===== SECTION 1: SELECT OR CREATE ROUTINE =====
            st.subheader("Step 1: Choose Your Routine")
            
            if routines:
                routine_options = ["Create New Routine"] + [f"{r['routine_name']} ({r['day_name']})" for r in routines]
                selected_option = st.selectbox("Select Routine", routine_options)
                
                if selected_option == "Create New Routine":
                    create_new_routine = True
                    selected_routine = None
                else:
                    create_new_routine = False
                    routine_idx = routine_options.index(selected_option) - 1
                    selected_routine = routines[routine_idx]
            else:
                st.info("👉 No routines yet. Let's create your first one!")
                create_new_routine = True
                selected_routine = None
            
            # ===== CREATE NEW ROUTINE =====
            if create_new_routine:
                st.divider()
                st.subheader("Create New Routine")
                
                with st.form(key='create_routine_form'):
                    col1, col2 = st.columns(2)
                    with col1:
                        routine_name = st.text_input("Routine Name", placeholder="e.g., Chest Day")
                    with col2:
                        day_name = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                    
                    description = st.text_area("Description (optional)", placeholder="Notes about this routine")
                    
                    submit = st.form_submit_button("Create Routine", type="primary", use_container_width=True)
                
                if submit and routine_name:
                    # ✅ CHECK: Only ONE routine per day allowed
                    day_already_has_routine = any(r['day_name'] == day_name for r in routines)
                    
                    if day_already_has_routine:
                        st.error(f"❌ You already have a routine for {day_name}! Each day can only have ONE routine.")
                    else:
                        routine_id = db.create_routine(
                            user_id=st.session_state['username'],
                            routine_name=routine_name,
                            day_name=day_name,
                            description=description
                        )
                        if routine_id:
                            st.success(f"✅ Routine '{routine_name}' created for {day_name}!")
                            st.rerun()
            
            # ===== WORK WITH SELECTED ROUTINE =====
            if selected_routine:
                st.divider()
                st.subheader(f"📋 {selected_routine['routine_name']} - {selected_routine['day_name']}")
                
                # Get exercises in this routine
                exercises = db.get_routine_exercises(selected_routine['id'])
                
                # ===== ADD NEW EXERCISE TO ROUTINE =====
                with st.expander("➕ Add Exercise to This Routine", expanded=not bool(exercises)):
                    with st.form(key='add_exercise_form'):
                        exercise_name = st.text_input(
                            "Exercise Name",
                            placeholder="e.g., Bench Press, Squat, Deadlift"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            target_muscle = st.selectbox("Target Muscle", MUSCLE_GROUPS)
                        with col2:
                            num_sets = st.number_input("Number of Sets", min_value=1, max_value=10, value=3)
                        
                        submit_ex = st.form_submit_button("Add Exercise to Routine", type="primary", use_container_width=True)
                    
                    if submit_ex and exercise_name:
                        success = db.add_routine_exercise(
                            routine_id=selected_routine['id'],
                            exercise_name=exercise_name,
                            target_muscle=target_muscle,
                            sets=num_sets,
                            reps=None,
                            weight=None,
                            notes="",
                            effort_level="Medium"
                        )
                        if success:
                            st.success(f"✅ Added {exercise_name}!")
                            st.rerun()
                
                # ===== LOG TODAY'S WORKOUT =====
                # ===== LOG TODAY'S WORKOUT =====
                if exercises:
                    st.divider()
                    st.subheader("Step 2: Log Today's Workout")
                    
                    all_set_details = {}
                    
                    for idx, ex in enumerate(exercises):  # ← Add enumerate index
                        st.markdown(f"### {ex['exercise_name']} ({ex['target_muscle']})")
                        st.caption(f"Target: {ex['sets']} sets")
                        
                        # Use a unique key with both exercise ID and enumerate index
                        actual_sets = st.number_input(
                            "Number of Sets Completed",
                            min_value=1,
                            max_value=10,
                            value=ex['sets'],
                            key=f"num_sets_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_idx_{idx}"
                        )
                        
                        set_details = []
                        for set_num in range(1, actual_sets + 1):
                            st.markdown(f"**Set {set_num}:**")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                reps = st.number_input(
                                    f"Reps",
                                    min_value=1,
                                    max_value=100,
                                    value=ex.get('reps') or 10,
                                    key=f"reps_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_idx_{idx}"
                                )
                            
                            with col2:
                                weight = st.number_input(
                                    f"Weight (kg)",
                                    min_value=0.0,
                                    max_value=500.0,
                                    value=float(ex.get('weight') or 0),
                                    step=2.5,
                                    key=f"weight_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_idx_{idx}"
                                )
                            
                            with col3:
                                effort = st.selectbox(
                                    f"Effort Level",
                                    ["Easy", "Medium", "Hard"],
                                    index=1,
                                    key=f"effort_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_idx_{idx}"
                                )
                            
                            set_details.append({
                                "reps": reps,
                                "weight": weight,
                                "effort": effort
                            })
                        
                        notes = st.text_area(
                            "Notes (optional)",
                            placeholder="How did it feel? Any observations?",
                            key=f"notes_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_idx_{idx}",
                            height=60
                        )
                        
                        all_set_details[ex['id']] = {
                            "exercise_name": ex['exercise_name'],
                            "target_muscle": ex['target_muscle'],
                            "sets": set_details,
                            "notes": notes,
                            "routine_id": selected_routine['id']
                        }
                        
                        st.divider()
                    
                    # ===== LOG ALL BUTTON =====
                    if st.button("💾 Log This Workout", type="primary", use_container_width=True):
                        total_sets_logged = 0
                        
                        for ex_id, details in all_set_details.items():
                            for set_data in details['sets']:
                                success = db.add_workout(
                                    user_id=st.session_state['username'],
                                    exercise_name=details['exercise_name'],
                                    target_muscle=details['target_muscle'],
                                    sets=1,
                                    reps=set_data['reps'],
                                    weight=set_data['weight'],
                                    notes=details['notes'],
                                    effort_level=set_data['effort'],
                                    routine_id=details['routine_id']
                                )
                                if success:
                                    total_sets_logged += 1
                        
                        st.success(f"✅ Logged {total_sets_logged} sets from {len(all_set_details)} exercises!")
                        st.balloons()
                        st.rerun()
                else:
                    st.info("👆 Add exercises to this routine first!")

        
        # ===== PAGE 2: VIEW HISTORY (GROUPED BY ROUTINE/DATE/EXERCISE) =====
# ===== PAGE 2: VIEW HISTORY (WITH DELETE BUTTON) =====
        elif page == "View History":
            st.header("📊 Workout History")
            
            # Fetch all workouts
            all_workouts = db.get_user_workouts(st.session_state['username'], limit=1000)
            
            if not all_workouts:
                st.info("📌 No workouts logged yet!")
            else:
                # Get routines for grouping
                routines = db.get_user_routines(st.session_state['username'])
                routine_map = {r['id']: r for r in routines}
                
                # Group: Routine → Date → Exercise → Sets
                grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
                
                for w in all_workouts:
                    routine_id = w.get('routine_id')
                    date_str = str(w['date'])[:10]  # YYYY-MM-DD
                    exercise_name = w['exercise_name']
                    
                    if routine_id:
                        grouped[routine_id][date_str][exercise_name].append(w)
                
                # ===== DISPLAY GROUPED VIEW =====
                if grouped:
                    for routine_id, date_dict in grouped.items():
                        routine = routine_map.get(routine_id, {})
                        routine_header = f"🏋️ {routine.get('routine_name', 'Unknown')} ({routine.get('day_name', '?')})"
                        
                        with st.expander(routine_header, expanded=True):
                            # Sort dates descending (newest first)
                            for workout_date in sorted(date_dict.keys(), reverse=True):
                                exercise_dict = date_dict[workout_date]
                                
                                with st.expander(f"📅 {workout_date}"):
                                    # Show each exercise on this date
                                    for exercise_name, sets in exercise_dict.items():
                                        st.markdown(f"**{exercise_name}**")
                                        
                                        for idx, s in enumerate(sets, 1):
                                            # Create columns with delete button
                                            col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1, 1.2, 1, 1.5, 0.8])
                                            
                                            with col1:
                                                st.write(f"Set {idx}")
                                            with col2:
                                                st.write(f"Reps: {s['reps']}")
                                            with col3:
                                                st.write(f"Weight: {s['weight']} kg" if s['weight'] else "No weight")
                                            with col4:
                                                st.write(f"Effort: {s.get('effort_level', 'N/A')}")
                                            with col5:
                                                st.write(f"Notes: {s['notes'][:20] + '...' if s['notes'] and len(s['notes']) > 20 else s['notes'] or '-'}")
                                            with col6:
                                                # Delete button for each set
                                                if st.button(
                                                    "🗑️",
                                                    key=f"delete_{s['id']}",
                                                    help="Delete this set"
                                                ):
                                                    if db.delete_workout(s['id']):
                                                        st.success("✅ Set deleted!")
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ Failed to delete set")
                                        
                                        st.divider()
                else:
                    st.info("📌 No grouped data available")

        
        # ===== PAGE 3: STATISTICS =====
        elif page == "Statistics":
            st.header("📈 Statistics & Progress")
            
            all_workouts = db.get_user_workouts(st.session_state['username'], limit=1000)
            
            if not all_workouts:
                st.info("📌 Log some workouts to see your statistics!")
            else:
                df = pd.DataFrame(all_workouts)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Workouts", len(all_workouts))
                with col2:
                    st.metric("Total Sets", df['sets'].sum())
                with col3:
                    st.metric("Total Reps", (df['sets'] * df['reps']).sum())
                with col4:
                    total_volume = (df['sets'] * df['reps'] * df['weight']).sum()
                    st.metric("Total Volume (kg)", f"{total_volume:,.0f}")
                
                st.divider()
                
                st.subheader("Workouts by Muscle Group")
                st.bar_chart(df['target_muscle'].value_counts())
                
                st.divider()
                
                if 'effort_level' in df.columns:
                    st.subheader("Effort Level Distribution")
                    effort_counts = df['effort_level'].value_counts()
                    st.bar_chart(effort_counts)
        
        st.sidebar.divider()
        st.sidebar.caption("💪 Stay Strong!")
    
    elif st.session_state.get("authentication_status") == False:
        st.error('❌ Username/password is incorrect')
        st.info("👉 Need an account? Go to the **Sign Up** tab!")
    
    elif st.session_state.get("authentication_status") == None:
        st.info("👉 Please enter your username and password to login")
        st.info("📌 **Don't have an account?** Go to the **Sign Up** tab!")

# ===== TAB 2: SIGN UP =====
with tab2:
    st.title("📝 Sign Up - Create Your Account")
    st.info("✨ **Create a free account to start tracking your workouts!**")
    st.subheader("Create Account")
    
    with st.form(key='registration_form'):
        new_email = st.text_input("Email", placeholder="you@example.com")
        new_username = st.text_input("Username", placeholder="john_fitness", help="Username for login")
        new_password = st.text_input("Password", type="password", placeholder="Enter password")
        new_password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        
        submit_button = st.form_submit_button("Sign Up", type="primary", use_container_width=True)
    
    if submit_button:
        if not new_email or not new_username or not new_password:
            st.error("❌ Please fill in all fields!")
        elif new_password.strip() != new_password_confirm.strip():
            st.error("❌ Passwords do not match!")
        elif len(new_password) < 6:
            st.error("❌ Password must be at least 6 characters!")
        elif new_username in config['credentials']['usernames']:
            st.error(f"❌ Username '{new_username}' already exists!")
        else:
            config['credentials']['usernames'][new_username] = {
                'email': new_email,
                'name': new_username.replace('_', ' ').title(),
                'password': new_password
            }
            
            save_config(config)
            
            st.success("✅ **Account created successfully!**")
            st.info(f"""
            **Welcome {new_username}!** 🎉
            
            Your account has been created:
            - **Email:** {new_email}
            - **Username:** {new_username}
            
            👉 Now go to the **Login** tab and log in with your credentials!
            """)
            
            st.rerun()

# ===== TAB 3: ABOUT =====
with tab3:
    st.title("ℹ️ About Workout Tracker")
    
    st.markdown("""
    ### 💪 Welcome to Your Personal Workout Tracker!
    
    This app helps you track your fitness journey with features including:
    
    #### 📝 **Log Workouts**
    - Record exercise name, target muscle group
    - Track sets, reps, and weight
    - Add notes about your performance
    - Rate effort level (Easy/Medium/Hard)
    
    #### 📊 **View History**
    - See all your workouts organized by routine
    - View each workout day and exercise details
    - Grouped by routine for better organization
    
    #### 📈 **Statistics**
    - Total workouts logged
    - Total sets and reps completed
    - Total volume lifted
    - Visual breakdown by muscle group
    - Effort level distribution
    
    #### 🔐 **Secure & Personal**
    - Create your own account (free!)
    - Your data is private and stored securely
    - Access from any device with a browser
    - One routine per day for better organization
    
    ### 🚀 Getting Started
    
    1. **Sign Up:** Click the "Sign Up" tab to create your account
    2. **Log In:** Use your credentials to log in
    3. **Create Routine:** Set up your daily routines (One per day)
    4. **Start Tracking:** Log your first workout!
    
    ### 💡 Important Notes
    
    - **One Routine Per Day:** You can only have ONE routine for each day (e.g., Monday can only have "Chest" not "Chest" AND "Back")
    - **Log workouts immediately** after your session for accuracy
    - **Add notes** about how the exercise felt
    - **Use effort levels** (Easy/Medium/Hard) to track intensity
    - **Check your statistics** regularly to track progress
    
    ---
    
    **Built with ❤️ using Streamlit, Supabase, and Python**
    """)
