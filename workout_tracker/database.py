"""
Database operations for workout tracker using Supabase
"""
from supabase import create_client, Client
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

def _norm_name(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()

class WorkoutDatabase:
    """Handle all database operations for the workout tracker"""

    def __init__(self):
        """Initialize Supabase connection"""
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            self.supabase: Client = create_client(url, key)
        except Exception as e:
            st.error(f"Failed to connect to database: {e}")
            self.supabase = None

    # ===== ROUTINES =====
    def create_routine(self, user_id: str, routine_name: str, day_name: str, description: str = "") -> Optional[int]:
        """Create a new routine and return its id (routine_name stored normalized)"""
        try:
            data = {
                "user_id": user_id,
                "routine_name": _norm_name(routine_name),
                "day_name": day_name,
                "description": description,
                # removed created_at to avoid PGRST204 if column doesn't exist
            }
            response = self.supabase.table("routines").insert(data).execute()
            if isinstance(response.data, list) and len(response.data) > 0:
                return response.data[0].get('id')
            elif isinstance(response.data, dict):
                return response.data.get('id')
            return None
        except Exception as e:
            st.error(f"Error creating routine: {e}")
            return None

    def get_user_routines(self, user_id: str) -> List[Dict]:
        """Get all routines for a user"""
        try:
            response = self.supabase.table("routines")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("day_name")\
                .execute()
            return response.data or []
        except Exception as e:
            st.error(f"Error fetching routines: {e}")
            return []

    def add_routine_exercise(
        self,
        routine_id: int,
        exercise_name: str,
        target_muscle: str,
        sets: int,
        reps: int = None,
        weight: float = None,
        notes: str = "",
        effort_level: str = "Medium",
        order_num: int = 1
    ) -> Optional[int]:
        """
        Add an exercise template to a routine.
        Stores exercise_name normalized (lower-case).
        Returns inserted routine_exercise id.
        """
        try:
            ex_key = _norm_name(exercise_name)

            # Since we normalize names, equality is enough (no ILIKE wildcards needed)
            existing = self.supabase.table("routine_exercises")\
                .select("id")\
                .eq("routine_id", routine_id)\
                .eq("exercise_name", ex_key)\
                .execute()
            if existing.data:
                return existing.data[0]["id"]

            data = {
                "routine_id": routine_id,
                "exercise_name": ex_key,  # normalized storage
                "target_muscle": target_muscle,
                "sets": sets,
                "order_num": order_num,
                # removed created_at to avoid PGRST204 if column doesn't exist
            }
            response = self.supabase.table("routine_exercises").insert(data).execute()
            if response.data:
                return response.data[0].get("id")
            return None
        except Exception as e:
            st.error(f"Error adding routine exercise: {e}")
            return None

    def get_routine_exercises(self, routine_id: int) -> List[Dict]:
        """Get all exercises in a routine"""
        try:
            response = self.supabase.table("routine_exercises")\
                .select("*")\
                .eq("routine_id", routine_id)\
                .order("order_num")\
                .execute()
            return response.data or []
        except Exception as e:
            st.error(f"Error fetching routine exercises: {e}")
            return []

    def delete_routine(self, routine_id: int) -> bool:
        """Delete a routine (cascades to exercises if FK has ON DELETE CASCADE)"""
        try:
            _ = self.supabase.table("routines").delete().eq("id", routine_id).execute()
            return True
        except Exception as e:
            st.error(f"Error deleting routine: {e}")
            return False

    def create_tables(self):
        """
        SQL to create tables in Supabase (run once in Supabase SQL Editor).

        -- Routines
        CREATE TABLE IF NOT EXISTS routines (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            routine_name TEXT NOT NULL,
            day_name TEXT NOT NULL,
            description TEXT
            -- created_at TIMESTAMP DEFAULT NOW()  -- optional
        );

        -- Routine exercises
        CREATE TABLE IF NOT EXISTS routine_exercises (
            id BIGSERIAL PRIMARY KEY,
            routine_id BIGINT NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
            exercise_name TEXT NOT NULL,
            target_muscle TEXT NOT NULL,
            sets INTEGER NOT NULL,
            order_num INTEGER DEFAULT 1
            -- created_at TIMESTAMP DEFAULT NOW()  -- optional
        );

        -- Prevent duplicates within a routine (case-insensitive)
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_routine_exercise_name
          ON routine_exercises (routine_id, lower(exercise_name));

        -- Workouts (per-set logs)
        CREATE TABLE IF NOT EXISTS workouts (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            date TIMESTAMP DEFAULT NOW(),
            routine_id BIGINT REFERENCES routines(id) ON DELETE SET NULL,
            routine_exercise_id BIGINT REFERENCES routine_exercises(id) ON DELETE SET NULL,
            exercise_name TEXT NOT NULL,
            target_muscle TEXT NOT NULL,
            sets INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight DECIMAL(6,2) NOT NULL,
            notes TEXT,
            effort_level TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_workouts_user_id ON workouts(user_id);
        CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
        CREATE INDEX IF NOT EXISTS idx_workouts_routine_exercise_id ON workouts(routine_exercise_id);
        """
        pass

    # ===== WORKOUTS =====
    def add_workout(
        self,
        user_id: str,
        exercise_name: str,
        target_muscle: str,
        sets: int,
        reps: int,
        weight: float,
        notes: str = "",
        effort_level: str = "Medium",
        routine_id: int = None,
        routine_exercise_id: int = None
    ) -> bool:
        """Add a new workout entry; stores routine_exercise_id and normalized exercise_name."""
        try:
            data = {
                "user_id": user_id,
                "date": datetime.now().isoformat(),
                "exercise_name": _norm_name(exercise_name),
                "target_muscle": target_muscle,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "notes": notes,
                "effort_level": effort_level,
                "routine_id": routine_id,
                "routine_exercise_id": routine_exercise_id
            }
            _ = self.supabase.table("workouts").insert(data).execute()
            return True
        except Exception as e:
            st.error(f"Error adding workout: {e}")
            return False

    def get_workouts_by_muscle(self, user_id: str, muscle: str) -> List[Dict]:
        try:
            response = self.supabase.table("workouts")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("target_muscle", muscle)\
                .order("date", desc=True)\
                .execute()
            return response.data or []
        except Exception as e:
            st.error(f"Error fetching workouts by muscle: {e}")
            return []

    def get_workouts_by_exercise(self, user_id: str, exercise: str) -> List[Dict]:
        try:
            response = self.supabase.table("workouts")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("exercise_name", _norm_name(exercise))\
                .order("date", desc=True)\
                .execute()
            return response.data or []
        except Exception as e:
            st.error(f"Error fetching workouts by exercise: {e}")
            return []

    def update_workout(self, workout_id: int, updates: Dict) -> bool:
        try:
            if "exercise_name" in updates:
                updates["exercise_name"] = _norm_name(updates["exercise_name"])
            _ = self.supabase.table("workouts").update(updates).eq("id", workout_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating workout: {e}")
            return False

    def delete_workout(self, workout_id: int) -> bool:
        try:
            _ = self.supabase.table("workouts").delete().eq("id", workout_id).execute()
            return True
        except Exception as e:
            st.error(f"Error deleting workout: {e}")
            return False

    def get_exercise_stats(self, user_id: str, exercise_name: str) -> Dict:
        try:
            workouts = self.get_workouts_by_exercise(user_id, exercise_name)
            if not workouts:
                return {}
            weights = [w.get('weight', 0) or 0 for w in workouts]
            total_sets = sum(w.get('sets', 0) or 0 for w in workouts)
            total_reps = sum(w.get('reps', 0) or 0 for w in workouts)
            return {
                "total_workouts": len(workouts),
                "max_weight": max(weights) if weights else 0,
                "avg_weight": (sum(weights) / len(weights)) if weights else 0,
                "total_sets": total_sets,
                "total_reps": total_reps
            }
        except Exception as e:
            st.error(f"Error calculating stats: {e}")
            return {}

    def get_user_workouts(self, user_id: str, limit: int = 100) -> list:
        """Return all workouts (most recent first)."""
        try:
            response = self.supabase.table("workouts").select("*")\
                .eq("user_id", user_id)\
                .order("date", desc=True)\
                .limit(limit)\
                .execute()
            return response.data or []
        except Exception as e:
            st.error(f"Error getting workouts: {e}")
            return []
