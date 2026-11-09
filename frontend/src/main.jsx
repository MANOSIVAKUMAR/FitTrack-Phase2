import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import api from "./api";
import "./style.css";

const today = new Date().toISOString().slice(0, 10);

function App() {
  const [token, setToken] = useState(localStorage.getItem("fittrack_token"));
  const [user, setUser] = useState(null);
  const [register, setRegister] = useState(false);
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState("dashboard");
  const [data, setData] = useState({ dashboard: null, workouts: [], plans: [], exercises: [], badges: [], myBadges: [], streak: null, goals: [], comparison: null });
  const [workout, setWorkout] = useState({ workout_name: "", category: "Cardio", duration: 30, calories_burned: 150, workout_date: today });
  const [plan, setPlan] = useState({ title: "", description: "", scheduled_date: today });
  const [exerciseSearch, setExerciseSearch] = useState("");
  const [goal, setGoal] = useState({ goal_type: "Weight Loss", target_value: 10, current_value: 0, deadline: today });

  useEffect(() => { if (token) loadAll(); }, [token]);

  async function loadAll() {
    try {
      const [me, dashboard, workouts, plans, exercises, badges, myBadges, streak, goals, comparison] = await Promise.all([
        api.get("/auth/me"), api.get("/dashboard"), api.get("/workouts"), api.get("/workout-plans?upcoming_only=true"),
        api.get("/exercises"), api.get("/badges"), api.get("/badges/my"), api.get("/streak"), api.get("/goals"), api.get("/comparison/weekly")
      ]);
      setUser(me.data); setData({ dashboard: dashboard.data, workouts: workouts.data, plans: plans.data, exercises: exercises.data, badges: badges.data, myBadges: myBadges.data, streak: streak.data, goals: goals.data, comparison: comparison.data });
    } catch (e) { setMsg(e.response?.data?.detail || "Unable to load data"); }
  }

  function logout() { localStorage.removeItem("fittrack_token"); setToken(null); setUser(null); }
  async function auth(e) {
    e.preventDefault(); setMsg("");
    try {
      if (register) { await api.post("/auth/register", form); setMsg("Registered successfully. Please login."); setRegister(false); }
      else { const r = await api.post("/auth/login", { email: form.email, password: form.password }); localStorage.setItem("fittrack_token", r.data.access_token); setToken(r.data.access_token); }
    } catch (e) { setMsg(e.response?.data?.detail || "Request failed"); }
  }
  async function addWorkout(e) { e.preventDefault(); try { await api.post("/workouts", workout); setMsg("Workout added"); setWorkout({ ...workout, workout_name: "" }); loadAll(); } catch(e) { setMsg(e.response?.data?.detail || "Request failed"); } }
  async function addPlan(e) { e.preventDefault(); try { await api.post("/workout-plans", plan); setMsg("Workout plan scheduled"); setPlan({ ...plan, title: "", description: "" }); loadAll(); } catch(e) { setMsg(e.response?.data?.detail || "Request failed"); } }
  async function addGoal(e) { e.preventDefault(); try { await api.post("/goals", goal); setMsg("Goal created"); loadAll(); } catch(e) { setMsg(e.response?.data?.detail || "Request failed"); } }
  async function searchExercises(e) { e.preventDefault(); const r = await api.get(`/exercises?search=${encodeURIComponent(exerciseSearch)}`); setData(d => ({ ...d, exercises: r.data })); }
  async function useExercise(id) { await api.post(`/workouts/from-exercise/${id}?workout_date=${today}`); setMsg("Exercise added to today's workouts"); loadAll(); }

  if (!token) return <div className="center"><div className="card auth"><h1>FitTrack</h1><p className="muted">Advanced Tracking & User Engagement</p><form onSubmit={auth}>{register && <input placeholder="Username" value={form.username} onChange={e=>setForm({...form,username:e.target.value})} required />}<input type="email" placeholder="Email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required/><input type="password" placeholder="Password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required/><button>{register?"Create account":"Login"}</button></form><p>{msg}</p><button className="link" onClick={()=>{setRegister(!register);setMsg("")}}>{register?"Back to Login":"Create account"}</button></div></div>;

  return <div className="page">
    <header><div><h1>FitTrack</h1><span className="muted">Welcome, {user?.username}</span></div><button onClick={logout}>Logout</button></header>
    <nav>{[["dashboard","Dashboard"],["workouts","Workouts"],["plans","Schedule"],["exercises","Exercises"],["goals","Goals"],["progress","Progress"],["achievements","Achievements"]].map(([id,label])=><button className={tab===id?"active":""} onClick={()=>setTab(id)} key={id}>{label}</button>)}</nav>
    {msg && <div className="notice">{msg}</div>}
    {tab==="dashboard" && <section><h2>Personalized Dashboard</h2><div className="grid"> <Stat title="Today's Workouts" value={data.dashboard?.daily_summary?.workouts ?? 0}/><Stat title="Calories" value={data.dashboard?.daily_summary?.calories ?? 0}/><Stat title="Current Streak" value={`${data.streak?.current_streak ?? 0} days`}/><Stat title="Longest Streak" value={`${data.streak?.longest_streak ?? 0} days`}/></div><div className="two"><Panel title="Upcoming Workouts">{data.plans.slice(0,5).map(p=><div className="item" key={p.id}><b>{p.title}</b><span>{p.scheduled_date}</span><small>{p.description}</small></div>)}{!data.plans.length&&<p className="muted">No upcoming plans.</p>}</Panel><Panel title="Goal Progress">{data.goals.map(g=><div className="item" key={g.id}><b>{g.goal_type}</b><span>{Math.round(Math.min(g.current_value/g.target_value*100,100))}%</span><small>{g.current_value} / {g.target_value}</small></div>)}{!data.goals.length&&<p className="muted">No goals yet.</p>}</Panel></div></section>}
    {tab==="workouts" && <section><h2>Workout Management</h2><form className="formgrid" onSubmit={addWorkout}><input placeholder="Workout name" value={workout.workout_name} onChange={e=>setWorkout({...workout,workout_name:e.target.value})} required/><select value={workout.category} onChange={e=>setWorkout({...workout,category:e.target.value})}><option>Cardio</option><option>Strength</option><option>Yoga</option></select><input type="number" placeholder="Duration" value={workout.duration} onChange={e=>setWorkout({...workout,duration:+e.target.value})}/><input type="number" placeholder="Calories" value={workout.calories_burned} onChange={e=>setWorkout({...workout,calories_burned:+e.target.value})}/><input type="date" value={workout.workout_date} onChange={e=>setWorkout({...workout,workout_date:e.target.value})}/><button>Add Workout</button></form><div className="list">{data.workouts.map(w=><div className="item" key={w.id}><b>{w.workout_name}</b><span>{w.category} · {w.duration} min · {w.calories_burned} cal · {w.workout_date}</span></div>)}</div></section>}
    {tab==="plans" && <section><h2>Workout Plans & Scheduling</h2><form className="formgrid" onSubmit={addPlan}><input placeholder="Plan title" value={plan.title} onChange={e=>setPlan({...plan,title:e.target.value})} required/><input placeholder="Description" value={plan.description} onChange={e=>setPlan({...plan,description:e.target.value})}/><input type="date" value={plan.scheduled_date} onChange={e=>setPlan({...plan,scheduled_date:e.target.value})}/><button>Schedule Workout</button></form><div className="list">{data.plans.map(p=><div className="item" key={p.id}><b>{p.title}</b><span>{p.scheduled_date}</span><small>{p.description}</small></div>)}</div></section>}
    {tab==="exercises" && <section><h2>Exercise Library</h2><form onSubmit={searchExercises} className="search"><input placeholder="Search exercises" value={exerciseSearch} onChange={e=>setExerciseSearch(e.target.value)}/><button>Search</button></form><div className="gridcards">{data.exercises.map(x=><div className="card" key={x.id}><h3>{x.name}</h3><span className="tag">{x.category}</span><p>{x.description}</p><small>{x.duration} min</small><button onClick={()=>useExercise(x.id)}>Add to today's workout</button></div>)}</div></section>}
    {tab==="goals" && <section><h2>Goals</h2><form className="formgrid" onSubmit={addGoal}><select value={goal.goal_type} onChange={e=>setGoal({...goal,goal_type:e.target.value})}><option>Weight Loss</option><option>Muscle Gain</option><option>Steps</option></select><input type="number" value={goal.target_value} onChange={e=>setGoal({...goal,target_value:+e.target.value})} placeholder="Target"/><input type="number" value={goal.current_value} onChange={e=>setGoal({...goal,current_value:+e.target.value})} placeholder="Current"/><input type="date" value={goal.deadline} onChange={e=>setGoal({...goal,deadline:e.target.value})}/><button>Create Goal</button></form>{data.goals.map(g=><div className="item" key={g.id}><b>{g.goal_type}</b><span>{g.current_value}/{g.target_value} · deadline {g.deadline}</span></div>)}</section>}
    {tab==="progress" && <section><h2>Progress Comparison</h2><div className="grid"><Stat title="This Week Workouts" value={data.comparison?.current?.workouts ?? 0}/><Stat title="Last Week Workouts" value={data.comparison?.previous?.workouts ?? 0}/><Stat title="Workout Change" value={data.comparison?.improvement?.workouts ?? 0}/><Stat title="Calories Change" value={data.comparison?.improvement?.calories ?? 0}/></div><Panel title="Insight"><p>{(data.comparison?.improvement?.workouts ?? 0)>=0?"Great! Your workout count is improving or staying steady.":"Keep going — your consistency can improve this week."}</p></Panel></section>}
    {tab==="achievements" && <section><h2>Achievements & Streaks</h2><div className="grid"><Stat title="Current Streak" value={`${data.streak?.current_streak ?? 0} days`}/><Stat title="Longest Streak" value={`${data.streak?.longest_streak ?? 0} days`}/></div><h3>Earned Badges</h3><div className="gridcards">{data.myBadges.map(b=><div className="card badge" key={b.id}><div className="icon">{b.icon}</div><h3>{b.name}</h3><p>{b.description}</p></div>)}{!data.myBadges.length&&<p className="muted">Complete workouts and streaks to earn badges.</p>}</div></section>}
  </div>;
}
const Stat=({title,value})=><div className="stat"><small>{title}</small><strong>{value}</strong></div>;
const Panel=({title,children})=><div className="panel"><h3>{title}</h3>{children}</div>;
createRoot(document.getElementById("root")).render(<App/>);
