"""
Database operations for workout tracker using Supabase
"""
from supabase import create_client, Client
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

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
            
    # ===== ROUTINES FUNCTIONS =====

    def create_routine(self, user_id: str, routine_name: str, day_name: str, description: str = "") -> bool:
        """Create a new routine"""
        try:
            data = {
                "user_id": user_id,
                "routine_name": routine_name,
                "day_name": day_name,
                "description": description,
                "created_at": datetime.now().isoformat()
            }
            response = self.supabase.table("routines").insert(data).execute()

            # FIX: handle both dict & list formats
            if isinstance(response.data, list) and len(response.data) > 0:
                return response.data[0].get('id')
            elif isinstance(response.data, dict):
                return response.data.get('id')
            else:
                return False

        except Exception as e:
            st.error(f"Error creating routine: {e}")
            return False


    def get_user_routines(self, user_id: str) -> List[Dict]:
        """Get all routines for a user"""
        try:
            response = self.supabase.table("routines")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("day_name")\
                .execute()
            return response.data
        except Exception as e:
            st.error(f"Error fetching routines: {e}")
            return []

    def add_routine_exercise(self, routine_id: int, exercise_name: str, target_muscle: str, 
                            sets: int, reps: int = None, weight: float = None, 
                            notes: str = "", effort_level: str = "Medium", order_num: int = 1) -> bool:
        """Add exercise to a routine with effort level"""
        try:
            data = {
                "routine_id": routine_id,
                "exercise_name": exercise_name,
                "target_muscle": target_muscle,
                "sets": sets,
                "reps": reps,
                "weight": weight if weight and weight > 0 else None,
                "notes": notes,
                "effort_level": effort_level,  # NEW
                "order_num": order_num
            }
            response = self.supabase.table("routine_exercises").insert(data).execute()
            return bool(response.data)
        except Exception as e:
            st.error(f"Error adding routine exercise: {e}")
            return False

    def get_routine_exercises(self, routine_id: int) -> List[Dict]:
        """Get all exercises in a routine"""
        try:
            response = self.supabase.table("routine_exercises")\
                .select("*")\
                .eq("routine_id", routine_id)\
                .order("order_num")\
                .execute()
            return response.data
        except Exception as e:
            st.error(f"Error fetching routine exercises: {e}")
            return []

    def delete_routine(self, routine_id: int) -> bool:
        """Delete a routine (cascades to exercises)"""
        try:
            response = self.supabase.table("routines")\
                .delete()\
                .eq("id", routine_id)\
                .execute()
            return True
        except Exception as e:
            st.error(f"Error deleting routine: {e}")
            return False
            
        
    def create_tables(self):
        """
        SQL to create tables in Supabase (run this once in Supabase SQL Editor):
        
        CREATE TABLE IF NOT EXISTS workouts (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            date TIMESTAMP DEFAULT NOW(),
            exercise_name TEXT NOT NULL,
            target_muscle TEXT NOT NULL,
            sets INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight DECIMAL(5,2) NOT NULL,
            notes TEXT
        );
        
        CREATE INDEX idx_workouts_user_id ON workouts(user_id);
        CREATE INDEX idx_workouts_date ON workouts(date);
        """
        pass
    
    def add_workout(self, user_id: str, exercise_name: str, target_muscle: str, 
                sets: int, reps: int, weight: float, notes: str = "", 
                effort_level: str = "Medium", routine_id: int = None) -> bool:
        """Add a new workout entry with routine_id"""
        try:
            data = {
                "user_id": user_id,
                "date": datetime.now().isoformat(),
                "exercise_name": exercise_name,
                "target_muscle": target_muscle,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "notes": notes,
                "effort_level": effort_level,
                "routine_id": routine_id  # NEW
            }
            response = self.supabase.table("workouts").insert(data).execute()
            return True
        except Exception as e:
            st.error(f"Error adding workout: {e}")
            return False

    
    def get_workouts_by_muscle(self, user_id: str, muscle: str) -> List[Dict]:
        """Get workouts filtered by target muscle"""
        try:
            response = self.supabase.table("workouts")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("target_muscle", muscle)\
                .order("date", desc=True)\
                .execute()
            return response.data
        except Exception as e:
            st.error(f"Error fetching workouts by muscle: {e}")
            return []
        
    def get_workouts_by_exercise(self, user_id: str, exercise: str) -> List[Dict]:
        """Get workouts filtered by exercise name"""
        try:
            response = self.supabase.table("workouts")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("exercise_name", exercise)\
                .order("date", desc=True)\
                .execute()
            return response.data
        except Exception as e:
            st.error(f"Error fetching workouts by exercise: {e}")
            return []
    
    def update_workout(self, workout_id: int, updates: Dict) -> bool:
        """Update an existing workout"""
        try:
            response = self.supabase.table("workouts")\
                .update(updates)\
                .eq("id", workout_id)\
                .execute()
            return True
        except Exception as e:
            st.error(f"Error updating workout: {e}")
            return False
    
    def delete_workout(self, workout_id: int) -> bool:
        """Delete a workout entry"""
        try:
            response = self.supabase.table("workouts")\
                .delete()\
                .eq("id", workout_id)\
                .execute()
            return True
        except Exception as e:
            st.error(f"Error deleting workout: {e}")
            return False
    
    def get_exercise_stats(self, user_id: str, exercise_name: str) -> Dict:
        """Get statistics for a specific exercise"""
        try:
            workouts = self.get_workouts_by_exercise(user_id, exercise_name)
            if not workouts:
                return {}
            
            weights = [w['weight'] for w in workouts]
            total_sets = sum(w['sets'] for w in workouts)
            total_reps = sum(w['reps'] for w in workouts)
            
            return {
                "total_workouts": len(workouts),
                "max_weight": max(weights),
                "avg_weight": sum(weights) / len(weights),
                "total_sets": total_sets,
                "total_reps": total_reps
            }
        except Exception as e:
            st.error(f"Error calculating stats: {e}")
            return {}
    
    def get_user_workouts(self, user_id: str, limit: int = 100) -> list:
        """
        Returns a list of all workouts for this user, most recent first,
        including routine_id and all other columns.
        """
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
    
    def delete_workout(self, workout_id: int) -> bool:

        try:
            response = self.supabase.table("workouts")\
                .delete()\
                .eq("id", workout_id)\
                .execute()
            return True
        except Exception as e:
            st.error(f"Error deleting workout: {e}")
            return False

