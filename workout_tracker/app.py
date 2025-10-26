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
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)
        if not isinstance(config, dict):
            raise ValueError("Parsed config.yaml is not a dict")
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
                        exercise_name = st.text_input("Exercise Name", placeholder="e.g., Bench Press, Squat, Deadlift")
                        col1, col2 = st.columns(2)
                        with col1:
                            target_muscle = st.selectbox("Target Muscle", MUSCLE_GROUPS)
                        with col2:
                            num_sets = st.number_input("Number of Sets (target)", min_value=1, max_value=10, value=3)

                        submit_ex = st.form_submit_button("Add Exercise to Routine", type="primary", use_container_width=True)

                    if submit_ex and exercise_name:
                        # Important: do NOT pass reps/weight/notes here (to avoid template rows appearing in History)
                        added = db.add_routine_exercise(
                            routine_id=selected_routine['id'],
                            exercise_name=exercise_name,
                            target_muscle=target_muscle,
                            sets=num_sets
                        )
                        if added:
                            st.success(f"✅ Added {exercise_name}!")
                            st.rerun()

                # ===== LOG TODAY'S WORKOUT =====
                if exercises:
                    st.divider()
                    st.subheader("Step 2: Log Today's Workout")

                    all_set_details = {}

                    for idx, ex in enumerate(exercises):
                        st.markdown(f"### {ex['exercise_name']} ({ex['target_muscle']})")
                        st.caption(f"Target: {ex['sets']} sets")
                        default_reps = 5
                        default_weight = 0.0

                        actual_sets = st.number_input(
                            "Number of Sets Completed",
                            min_value=0,
                            max_value=10,
                            value=int(ex['sets']) if isinstance(ex['sets'], int) else 0,
                            key=f"num_sets_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_idx_{idx}"
                        )
                        if actual_sets<1:
                            continue

                        set_details = []
                        for set_num in range(1, actual_sets + 1):
                            st.markdown(f"**Set {set_num}:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                reps = st.number_input(
                                    "Reps",
                                    min_value=1,
                                    max_value=100,
                                    value=default_reps,
                                    key=f"reps_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_uid_{idx}_{set_num}_{datetime.now().timestamp()}"
                                )
                            with col2:
                                weight = st.number_input(
                                    "Weight (kg)",
                                    min_value=0.0,
                                    max_value=500.0,
                                    value=default_weight,
                                    step=2.5,
                                    key=f"weight_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_uid_{idx}_{set_num}_{datetime.now().timestamp()}"
                                )
                            with col3:
                                effort = st.selectbox(
                                    "Effort Level",
                                    ["Easy", "Medium", "Hard"],
                                    index=1,
                                    key=f"effort_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_set_{set_num}_idx_{idx}"
                                )
                            set_details.append({"reps": reps, "weight": weight, "effort": effort})

                        notes = st.text_area(
                            "Notes (optional)",
                            placeholder="How did it feel? Any observations?",
                            key=f"notes_{selected_routine['id']}_{ex['exercise_name'].replace(' ', '_')}_idx_{idx}",
                            height=60
                        )

                        # CRITICAL: keep routine_exercise_id for each block
                        all_set_details[ex['id']] = {
                            "exercise_name": ex['exercise_name'],
                            "target_muscle": ex['target_muscle'],
                            "sets": set_details,
                            "notes": notes,
                            "routine_id": selected_routine['id'],
                            "routine_exercise_id": ex['id'],    # ← used when saving & grouping
                        }

                        st.divider()

                    # ===== LOG ALL BUTTON =====
                    if st.button("💾 Log This Workout", type="primary", use_container_width=True):
                        total_sets_logged = 0
                        for _, details in all_set_details.items():
                            for set_data in details['sets']:
                                ok = db.add_workout(
                                    user_id=st.session_state['username'],
                                    exercise_name=details['exercise_name'],
                                    target_muscle=details['target_muscle'],
                                    sets=1,
                                    reps=set_data['reps'],
                                    weight=set_data['weight'],
                                    notes=details['notes'],
                                    effort_level=set_data['effort'],
                                    routine_id=details['routine_id'],
                                    routine_exercise_id=details['routine_exercise_id']  # ← SAVE IT
                                )
                                if ok:
                                    total_sets_logged += 1
                        st.success(f"✅ Logged {total_sets_logged} sets from {len(all_set_details)} exercises!")
                        st.balloons()
                        st.rerun()
                else:
                    st.info("👆 Add exercises to this routine first!")

        # ===== PAGE 2: VIEW HISTORY =====
        elif page == "View History":
            st.header("📊 Workout History")
            all_workouts_raw = db.get_user_workouts(st.session_state['username'], limit=1000)

            if not all_workouts_raw:
                st.info("📌 No workouts logged yet!")
            else:
                # Keep only real set rows
                filtered = []
                for w in all_workouts_raw:
                    if not w:
                        continue
                    if w.get('reps') is not None and w.get('date') is not None:
                        filtered.append(w)

                if not filtered:
                    st.info("📌 No logged sets to display yet.")
                else:
                    # Build routine and exercise maps
                    routines = db.get_user_routines(st.session_state['username'])
                    routine_map = {r['id']: r for r in routines}
                    ex_map_per_routine = {}
                    for r in routines:
                        ex_list = db.get_routine_exercises(r['id']) or []
                        ex_map_per_routine[r['id']] = {
                            e['id']: {"name": e['exercise_name'], "muscle": e.get('target_muscle')}
                            for e in ex_list if e and 'id' in e
                        }

                    # Group: Routine → Date → RoutineExerciseID → rows
                    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
                    for w in filtered:
                        rid = w.get('routine_id')
                        reid = w.get('routine_exercise_id')
                        date_val = w.get('date')
                        date_str = str(date_val)[:10] if date_val else "Unknown"
                        if rid and reid:
                            grouped[rid][date_str][reid].append(w)
                        elif rid:
                            # fallback for old rows (unlikely once migration is done)
                            grouped[rid][date_str][("name", w.get('exercise_name'))].append(w)

                    if grouped:
                        for rid, date_dict in grouped.items():
                            rmeta = routine_map.get(rid, {})
                            header = f"🏋️ {rmeta.get('routine_name', 'Unknown')} ({rmeta.get('day_name', '?')})"
                            with st.expander(header, expanded=True):
                                for workout_date in sorted(date_dict.keys(), reverse=True):
                                    exid_dict = date_dict[workout_date]
                                    with st.expander(f"📅 {workout_date}"):
                                        for ex_key, rows in exid_dict.items():
                                            # resolve title
                                            if isinstance(ex_key, tuple) and ex_key[0] == "name":
                                                title = ex_key[1] or "Unknown Exercise"
                                            else:
                                                title = ex_map_per_routine.get(rid, {}).get(ex_key, {}).get("name", "Unknown Exercise")
                                            st.markdown(f"**{title}**")

                                            for idx, s in enumerate(rows, 1):
                                                col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1, 1.2, 1, 1.5, 0.8])
                                                with col1:
                                                    st.write(f"Set {idx}")
                                                with col2:
                                                    st.write(f"Reps: {s.get('reps','-')}")
                                                with col3:
                                                    wv = s.get('weight')
                                                    st.write(f"Weight: {wv} kg" if wv else "No weight")
                                                with col4:
                                                    st.write(f"Effort: {s.get('effort_level','N/A')}")
                                                with col5:
                                                    nv = s.get('notes') or ''
                                                    disp = (nv[:20] + '...') if len(nv) > 20 else (nv or '-')
                                                    st.write(f"Notes: {disp}")
                                                with col6:
                                                    sid = s.get('id')
                                                    if sid is not None and st.button("🗑️", key=f"delete_{sid}", help="Delete this set"):
                                                        if db.delete_workout(sid):
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
            all_workouts_raw = db.get_user_workouts(st.session_state['username'], limit=1000)

            if not all_workouts_raw:
                st.info("📌 Log some workouts to see your statistics!")
            else:
                filtered = [w for w in all_workouts_raw if w and w.get('reps') is not None]
                if not filtered:
                    st.info("📌 No logged sets yet to compute statistics.")
                else:
                    df = pd.DataFrame(filtered)
                    for col in ['sets', 'reps', 'weight']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                        else:
                            df[col] = 0

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Workouts", len(filtered))
                    with col2:
                        st.metric("Total Sets", int(df['sets'].sum()))
                    with col3:
                        st.metric("Total Reps", int((df['sets'] * df['reps']).sum()))
                    with col4:
                        total_volume = (df['sets'] * df['reps'] * df['weight']).sum()
                        st.metric("Total Volume (kg)", f"{total_volume:,.0f}")

                    st.divider()
                    st.subheader("Workouts by Muscle Group")
                    if 'target_muscle' in df.columns and not df['target_muscle'].isna().all():
                        st.bar_chart(df['target_muscle'].value_counts())
                    else:
                        st.info("No muscle group data available.")

                    st.divider()
                    if 'effort_level' in df.columns and not df['effort_level'].isna().all():
                        st.subheader("Effort Level Distribution")
                        effort_counts = df['effort_level'].value_counts()
                        st.bar_chart(effort_counts)
                    else:
                        st.info("No effort level data available.")

        st.sidebar.divider()
        st.sidebar.caption("💪 Stay Strong!")

    elif st.session_state.get("authentication_status") == False:
        st.error('❌ Username/password is incorrect')
        st.info("👉 Need an account? Go to the **Sign Up** tab!")
    elif st.session_state.get("authentication_status") is None:
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
            st.info(f"**Welcome {new_username}!** 🎉\n\n👉 Now go to the **Login** tab and log in with your credentials!")
            st.rerun()

# ===== TAB 3: ABOUT =====
with tab3:
    st.title("ℹ️ About Workout Tracker")
    st.markdown("""
    ### 💪 Welcome to Your Personal Workout Tracker!

    This app helps you log workouts, organize routines, and visualize progress.
    - One routine per day
    - Per-set logging with effort levels
    - Secure login
    """)
