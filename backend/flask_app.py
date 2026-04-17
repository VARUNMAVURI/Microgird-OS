from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from fpdf import FPDF

import sys
import uuid
import pandas as pd
import traceback
import datetime
from datetime import timedelta
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add Project Root and Backend to Path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.append(p)

from database.db_manager import DatabaseManager  # noqa: E402

from flask_wtf.csrf import CSRFProtect, generate_csrf
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'frontend', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'frontend', 'static'))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key_123")
app.permanent_session_lifetime = timedelta(days=7)

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Initialize Database
db = DatabaseManager(
    db_name=os.getenv("DATABASE_NAME", "microgrid_drl"),
    connection_string=os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
)

# House owner dataset loading is now handled via DB migration (import_data.py)
# owner_dataset = pd.read_csv(...) is removed for scalability.

# --- ROUTES ---

@app.route('/')
def index():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html', 
                          csrf_token=generate_csrf(),
                          mobile=session.get('user_mobile', ''),
                          step=request.args.get('step', '1'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    if session.get('user_role') == 'house_owner':
        return redirect(url_for('owner_home'))
    
    email = session['user_email']
    sim = get_sim(email)
    data_loaded = sim.df is not None
    
    return render_template('dashboard.html', email=email, data_loaded=data_loaded, csrf_token=generate_csrf())

@app.route('/owner_home')
def owner_home():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('owner_home.html', 
                           email=session['user_email'],
                           mobile=session.get('user_mobile', ''),
                           csrf_token=generate_csrf())

@app.route('/owner_setup')
def owner_setup():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('owner_setup.html', csrf_token=generate_csrf())

@app.route('/api/owner/setup', methods=['POST'])
def api_owner_setup():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    consumer_number = (data.get('consumer_number') or '').strip()
    
    if not consumer_number.isdigit() or not (6 <= len(consumer_number) <= 12):
        return jsonify({"success": False, "message": "Invalid Consumer Number. Must be 6–12 digits."}), 400
    
    # Validate against database (Scalable lookup)
    house_data = db.get_house_data(consumer_number)
    if not house_data:
        return jsonify({"success": False, "message": "Consumer Number not found in our records. Please check and try again."}), 404
        
    session['consumer_number'] = consumer_number
    # Permanently link meter to user account for security
    db.link_meter(session['user_email'], consumer_number)
    
    return jsonify({"success": True, "redirect": url_for('owner_home')})

@app.route('/history')
def history():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    user_history = db.get_user_history(session['user_email'])
    return render_template('history.html', email=session['user_email'], history=user_history)

@app.route('/energy_flow')
def energy_flow():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('energy_flow.html', email=session['user_email'])

@app.route('/visualization')
def visualization():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('visualization.html', email=session['user_email'])


@app.route('/settings')
def app_settings():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    user_settings = db.get_user_settings(session['user_email'])
    return render_template('settings.html', 
                           email=session['user_email'],
                           sender_email=user_settings.get("sender_email", ""),
                           sender_password=user_settings.get("sender_password", ""))

@app.route('/api/settings/email', methods=['POST'])
def save_email_settings():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    sender_email = data.get('sender_email', '').strip()
    sender_password = data.get('sender_password', '').strip()
    
    if not sender_email or not sender_password:
        return jsonify({"success": False, "message": "Both email and password are required"}), 400
        
    db.update_user_settings(session['user_email'], {
        "sender_email": sender_email,
        "sender_password": sender_password
    })
    
    return jsonify({"success": True, "message": "Email settings saved successfully"})

# --- API ENDPOINTS ---

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    role = data.get('role', 'community_admin')  # 'community_admin' or 'house_owner'
    mobile = (data.get('mobile') or '').strip() or session.get('user_mobile')
    otp = (data.get('otp') or '').strip()
    
    # 1. ALWAYS verify OTP first (Step 1) unless already verified in session
    is_pre_verified = not otp and session.get('otp_verified') and mobile == session.get('user_mobile')
    
    if not is_pre_verified:
        if not db.verify_otp(mobile, otp):
            return jsonify({"success": False, "message": "Invalid or expired OTP"}), 401
        # Set session on successful verification if not already there
        session['otp_verified'] = True
        session['user_mobile'] = mobile

    if role == 'community_admin':
        # 2. For Admins, verify Email and Password (Step 3) - Sign In Mode
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '')
        
        if not db.authenticate_user(email, password):
            return jsonify({"success": False, "message": "Invalid admin email or password"}), 401
            
        session.permanent = False
        session['user_email'] = email
        session['user_role'] = role
        session['user_mobile'] = mobile
        
        # Force dataset upload on login
        sim = get_sim(email)
        sim.df = None
        sim.dataset_name = "No Dataset Loaded"
        sim.current_step = 0
        sim.results = []
        
        return jsonify({"success": True, "redirect": url_for('dashboard')})
    
    else:
        # 3. For House Owners, OTP is enough
        user = db.find_user_by_mobile(mobile)
        session.permanent = False
        # Use existing email if found, otherwise use mobile as identifier
        session['user_email'] = (user.get('email') if user else None) or mobile
        session['user_mobile'] = mobile
        session['user_role'] = role
        # Redirect to owner_setup (Consumer ID page)
        return jsonify({"success": True, "redirect": url_for('owner_setup')})

from utils.sms_service import send_otp_sms, sms_service

@app.route('/api/request_otp', methods=['POST'])
def request_otp():
    data = request.json
    mobile = (data.get('mobile') or '').strip()
    
    if not mobile:
        return jsonify({"success": False, "message": "Mobile number is required"}), 400
        
    # Check if user exists, if not, auto-register
    user = db.find_user_by_mobile(mobile)
    if not user:
        print(f"DEBUG: Auto-registering new mobile user: {mobile}")
        success, msg = db.register_user(mobile=mobile)
        if not success:
            return jsonify({"success": False, "message": f"Auto-registration failed: {msg}"}), 500
        
    # Generate 6-digit OTP
    import random
    otp = str(random.randint(100000, 999999))
    
    # Store in DB
    db.store_otp(mobile, otp)
    
    # Send via real SMS in background to avoid delay
    import threading
    def send_async_otp(m, o):
        success, s_msg = send_otp_sms(m, o)
        print(f"DEBUG: Background OTP Send Result for {m}: {success} - {s_msg}")

    threading.Thread(target=send_async_otp, args=(mobile, otp), daemon=True).start()
    
    # Provide OTP in response ONLY if in mock mode for development purposes
    response_data = {
        "success": True, 
        "message": "OTP sent successfully",
        "expiry_seconds": 300 # 5 minutes
    }
    
    if getattr(sms_service, 'is_mock', False):
        response_data["debug_otp"] = otp
        response_data["message"] = f"DEBUG MODE: Use verification code {otp}"

    return jsonify(response_data)

@app.route('/api/verify_otp', methods=['POST'])
def verify_otp_endpoint():
    data = request.json
    mobile = (data.get('mobile') or '').strip()
    otp = (data.get('otp') or '').strip()
    
    if not mobile or not otp:
        return jsonify({"success": False, "message": "Mobile and OTP are required"}), 400
        
    if db.verify_otp(mobile, otp):
        session['otp_verified'] = True
        session['user_mobile'] = mobile
        return jsonify({"success": True, "message": "OTP verified successfully"})
    return jsonify({"success": False, "message": "Invalid or expired OTP"})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    mobile = (data.get('mobile') or '').strip() or session.get('user_mobile')
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    role = data.get('role')

    # Security check: Ensure OTP was verified in this session
    if not session.get('otp_verified') or mobile != session.get('user_mobile'):
        return jsonify({"success": False, "message": "Security Error: OTP verification required."}), 401

    if not email or not password or not role:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    success, msg = db.register_user(email, password, mobile)
    if success:
        session['user_email'] = email
        session['user_role'] = role
        session['user_mobile'] = mobile
        # Admins go to dashboard, Owners go to setup
        redirect_url = url_for('dashboard') if role == 'community_admin' else url_for('owner_setup')
        return jsonify({"success": True, "message": "Registration successful", "redirect": redirect_url})
    
    return jsonify({"success": False, "message": msg})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_email', None)
    return jsonify({"success": True, "redirect": url_for('index')})

@app.route('/switch_to_owner')
def switch_to_owner():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    # Seamless switch ONLY from community_admin
    if session.get('user_role') == 'community_admin':
        session['user_role'] = 'house_owner'
        # Always force re-identification by clearing any existing consumer_number
        session.pop('consumer_number', None)
        return redirect(url_for('owner_setup'))
    return redirect(url_for('dashboard'))

@app.route('/switch_to_admin')
def switch_to_admin():
    # Preserve mobile verification but clear role data to skip Step 1
    mobile = session.get('user_mobile')
    otp_verified = session.get('otp_verified')
    consumer_number = session.get('consumer_number')
    
    session.clear()
    
    if mobile:
        session['user_mobile'] = mobile
        session['otp_verified'] = otp_verified
    if consumer_number:
        session['consumer_number'] = consumer_number
        
    # Redirect to index and hint frontend to show role selection (Step 2)
    return redirect(url_for('index', step='2'))

@app.route('/api/history/delete', methods=['POST'])
def delete_history_item():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    simulation_id = data.get('simulation_id')
    
    if not simulation_id:
        return jsonify({"success": False, "message": "Missing simulation ID"}), 400
        
    success, msg = db.delete_simulation(session['user_email'], simulation_id)
    return jsonify({"success": success, "message": msg})

from backend.simulation_engine import SimulationEngine  # noqa: E402

# Global Simulation State (For demo purposes; ideally this would be redis/db backed per user)
# Key: user_email, Value: SimulationEngine instance
simulations = {}

def get_sim(email):
    email = (email or '').strip().lower()
    if email not in simulations:
        simulations[email] = SimulationEngine()
    sim = simulations[email]
    print(f"DEBUG get_sim({email}): df={'LOADED (' + str(len(sim.df)) + ' rows)' if sim.df is not None else 'NONE'}")
    return sim

@app.route('/api/simulation/start', methods=['POST'])
def start_simulation():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    mode = request.json.get('mode', 'AI') # 'AI' or 'RULE'
    speed_ms = request.json.get('speed', 700)
    
    print(f"DEBUG: Start Simulation Request from '{email}' mode={mode} speed={speed_ms}")
    print(f"DEBUG: Known simulation keys: {list(simulations.keys())}")
    sim = get_sim(email)
    
    # Enforce Dataset Upload
    if sim.df is None:
        print(f"DEBUG: Simulation for '{email}' has no data loaded!")
        return jsonify({"success": False, "message": "No dataset loaded. Please upload a CSV file first."})
        
    try:
        if not getattr(sim, 'is_running', False):
            # Only reset if we are starting from scratch (step 0), otherwise resume
            if sim.current_step == 0:
                print("DEBUG: Calling sim.reset()...")
                first_step = sim.reset()
                if first_step and first_step.get("error"):
                    print(f"DEBUG: sim.reset() returned error: {first_step.get('error')}")
                    return jsonify({"success": False, "message": f"Simulation Error: {first_step.get('error')}"})
            else:
                first_step = sim.results[-1] if sim.results else {}

            sim.is_running = True
            sim.sim_mode = mode
            sim.sim_speed_ms = speed_ms
            
            # Start Background Thread
            def run_simulation_loop(simulation_engine, user_email):
                import time
                print(f"🚀 Background thread started for {user_email}")
                while getattr(simulation_engine, 'is_running', False):
                    if simulation_engine.current_step >= len(simulation_engine.df):
                        simulation_engine.is_running = False
                        print(f"⏹️ Simulation Finished naturally for {user_email}")
                        
                        # Auto-Save Logic
                        analysis = simulation_engine.analyze_results()
                        suggestions = analysis.get("suggestions", [])
                        success, msg = db.save_simulation(user_email, {
                            "dataset": simulation_engine.dataset_name,
                            "sim_results": simulation_engine.results,
                            "full_data_length": len(simulation_engine.results),
                            "savings_pct": simulation_engine.results[-1].get("savings_pct") if simulation_engine.results else 0,
                            "net_profit": simulation_engine.results[-1].get("total_savings") if simulation_engine.results else 0,
                            "suggestions": suggestions,
                            "analysis": analysis,
                            "efficiency": simulation_engine.results[-1].get("efficiency") if simulation_engine.results else 0.0
                        })
                        if success:
                            print(f"✅ Auto-saved finished simulation for {user_email}")
                        break
                        
                    try:
                        step_data = simulation_engine.step(mode=simulation_engine.sim_mode)
                        if step_data.get("finished"):
                            simulation_engine.is_running = False
                            break
                    except Exception as e:
                        print(f"❌ Background sim error: {e}")
                        simulation_engine.is_running = False
                        break
                        
                    # Sleep based on UI speed
                    time.sleep(simulation_engine.sim_speed_ms / 1000.0)

            import threading
            target_thread = threading.Thread(target=run_simulation_loop, args=(sim, email))
            target_thread.daemon = True
            target_thread.start()
            
            print("DEBUG: Simulation thread started successfully.")
            return jsonify({
                "success": True, 
                "message": f"Simulation started in {mode} mode",
                "initial_state": first_step,
                "mode": mode
            })
        else:
            return jsonify({"success": True, "message": "Simulation already running"})
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Critical Error: {str(e)}"})

@app.route('/api/simulation/pause', methods=['POST'])
def simulation_pause():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    sim.is_running = False
    print(f"⏸️ Simulation Paused for {email}")
    return jsonify({"success": True, "message": "Simulation paused"})

@app.route('/api/simulation/reset', methods=['POST'])
def simulation_reset_endpoint():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    sim.is_running = False
    sim.reset()
    print(f"🔄 Simulation Reset for {email}")
    return jsonify({"success": True, "message": "Simulation reset"})

@app.route('/api/simulation/resume', methods=['POST'])
def simulation_resume():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    speed_ms = request.json.get('speed', getattr(sim, 'sim_speed_ms', 700))
    sim.sim_speed_ms = speed_ms
    
    if not getattr(sim, 'is_running', False):
        sim.is_running = True
        
        # We need to restart the background thread
        def run_simulation_loop(simulation_engine, user_email):
            import time
            print(f"🚀 Background thread RESUMED for {user_email}")
            while getattr(simulation_engine, 'is_running', False):
                if simulation_engine.current_step >= len(simulation_engine.df):
                    simulation_engine.is_running = False
                    print(f"⏹️ Simulation Finished naturally for {user_email}")
                    
                    # Auto-Save Logic
                    analysis = simulation_engine.analyze_results()
                    suggestions = analysis.get("suggestions", [])
                    success, msg = db.save_simulation(user_email, {
                        "dataset": simulation_engine.dataset_name,
                        "sim_results": simulation_engine.results,
                        "full_data_length": len(simulation_engine.results),
                        "savings_pct": simulation_engine.results[-1].get("savings_pct") if simulation_engine.results else 0,
                        "net_profit": simulation_engine.results[-1].get("total_savings") if simulation_engine.results else 0,
                        "suggestions": suggestions,
                        "analysis": analysis,
                        "efficiency": simulation_engine.results[-1].get("efficiency") if simulation_engine.results else 0.0
                    })
                    break
                    
                try:
                    step_data = simulation_engine.step(mode=simulation_engine.sim_mode)
                    if step_data.get("finished"):
                        simulation_engine.is_running = False
                        break
                except Exception as e:
                    print(f"❌ Background sim error: {e}")
                    simulation_engine.is_running = False
                    break
                    
                time.sleep(simulation_engine.sim_speed_ms / 1000.0)

        import threading
        target_thread = threading.Thread(target=run_simulation_loop, args=(sim, email))
        target_thread.daemon = True
        target_thread.start()
        
    return jsonify({"success": True, "message": "Simulation Resumed"})
    
@app.route('/api/simulation/speed', methods=['POST'])
def simulation_speed():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    data = request.json
    speed_ms = data.get('speed', 700)
    
    sim.sim_speed_ms = speed_ms
    print(f"⏱️ Simulation Speed Updated to {speed_ms}ms for {email}")
    return jsonify({"success": True, "message": f"Speed updated to {speed_ms}ms"})


@app.route('/api/simulation/step', methods=['POST'])
def simulation_step():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    mode = request.json.get('mode', 'AI')
    
    sim = get_sim(email)
    step_data = sim.step(mode=mode)
    print(f"DEBUG: Step {step_data.get('hour')} - Benchmark: {step_data.get('benchmark_savings')} - Savings: {step_data.get('total_savings')}")
    
    # Check for Simulation End & Auto-Save
    if step_data.get("finished"):
        # Run Analysis
        analysis = sim.analyze_results()
        suggestions = analysis.get("suggestions", [])
        
        # Save to DB
        success, msg = db.save_simulation(email, {
            "dataset": sim.dataset_name,
            "sim_results": sim.results, # Save FULL simulation history
            "full_data_length": len(sim.results),
            "savings_pct": sim.results[-1].get("savings_pct") if sim.results else 0,
            "net_profit": sim.results[-1].get("total_savings") if sim.results else 0,
            "suggestions": suggestions,
            "analysis": analysis,
            "efficiency": sim.results[-1].get("efficiency") if sim.results else 0.0
        })
        if success:
            print(f"✅ Auto-saved simulation for {email}")
            
        # Return suggestions with the final step to the frontend (optional, if we want to show immediately)
        step_data["suggestions"] = suggestions
    
    return jsonify(step_data)

@app.route('/history/view/<simulation_id>')
def view_simulation(simulation_id):
    if 'user_email' not in session:
        return redirect(url_for('index'))
        
    sim_data = db.get_simulation(simulation_id)
    if not sim_data:
        return "Simulation not found", 404
        
    # Ensure the user owns this simulation (Security Check)
    if sim_data.get('user_email') != session['user_email']:
        return "Unauthorized", 403
        
    return render_template('simulation_details.html', 
                           email=session['user_email'], 
                           simulation=sim_data)

@app.route('/suggestions')
def suggestions_page():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    
    # Get latest simulation
    user_history = db.get_user_history(session['user_email'])
    
    suggestions = []
    dataset_name = "Unknown"
    
    if user_history and len(user_history) > 0:
        latest_sim = user_history[0]
        # Check if 'suggestions' exists in summary
        if 'summary' in latest_sim and 'suggestions' in latest_sim['summary']:
            suggestions = latest_sim['summary']['suggestions']
        
        if 'data' in latest_sim and 'dataset' in latest_sim['data']:
            dataset_name = latest_sim['data']['dataset']
            
    return render_template('suggestions.html', 
                           email=session['user_email'], 
                           suggestions=suggestions,
                           dataset_name=dataset_name)

@app.route('/api/simulation/results', methods=['GET'])
def simulation_results():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    return jsonify({
        "results": sim.results,
        "current_step": sim.current_step
    })

@app.route('/api/simulation/status', methods=['GET'])
def simulation_status():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    latest_result = sim.results[-1] if sim.results else None
    
    # Check if the background thread is still running
    # This is a simplified check; a more robust solution might involve thread management
    # or a dedicated flag set by the thread itself.
    thread_running = getattr(sim, 'is_running', False)
    
    # Check for simulation errors
    error_msg = None
    if latest_result and isinstance(latest_result, dict) and latest_result.get("error"):
        error_msg = latest_result.get("error")
        # If it's a critical error, stop polling on frontend if possible, 
        # but here we just report it.
        
    return jsonify({
        "success": True,
        "running": thread_running,
        "step": sim.current_step,
        "total_steps": len(sim.df) if sim.df is not None else 0,
        "latest_result": latest_result,
        "error": error_msg,
        "dataset": sim.dataset_name if sim.df is not None else "No Dataset Loaded",
        "data_loaded": sim.df is not None,
        "benchmark_savings": getattr(sim, 'benchmark_savings', 0.0)
    })

def calculate_ap_bill(grid_import, grid_export):
    """
    Standard APSPDCL Slab-based billing logic for LT-1 Domestic.
    """
    units = float(grid_import)
    energy_charge = 0
    
    if units <= 50:
        energy_charge = units * 1.45
    elif units <= 100:
        energy_charge = (50 * 1.45) + ((units - 50) * 2.60)
    elif units <= 200:
        energy_charge = (50 * 1.45) + (50 * 2.60) + ((units - 100) * 3.60)
    else:
        energy_charge = (50 * 1.45) + (50 * 2.60) + (100 * 3.60) + ((units - 200) * 6.90)
    
    fixed_charge = 50.00
    customer_charge = 40.00
    ed_duty = units * 0.06 # Electricity Duty
    fsa_charge = units * 0.10 # Fuel Surcharge
    
    # Net Metering Credit
    feed_in_tariff = 4.00
    export_credit = float(grid_export) * feed_in_tariff
    
    total_current = energy_charge + fixed_charge + customer_charge + ed_duty + fsa_charge
    net_bill_amount = max(total_current - export_credit, 0)
    
    return {
        "energy_charge": round(energy_charge, 2),
        "fixed_charge": fixed_charge,
        "customer_charge": customer_charge,
        "ed_duty": round(ed_duty, 2),
        "fsa_charge": round(fsa_charge, 2),
        "export_credit": round(export_credit, 2),
        "total_current": round(total_current, 2),
        "final_bill": round(net_bill_amount, 2)
    }

@app.route('/api/billing/download')
def download_bill():
    if 'user_email' not in session:
        return "Unauthorized", 401
        
    email = (session['user_email'] or '').strip().lower()
    meter = request.args.get('meter', '').strip()
    if not meter:
        meter = session.get('consumer_number')
        
    if not meter:
        return "No consumer number found. Please load a meter first.", 400

    # Fetch House Data from DB
    data = db.get_house_data(meter)
    if not data:
        return f"Consumer records for Meter {meter} not found.", 404

    from flask import Response
    import datetime

    # Extract info for AP Board Format
    owner_name = data.get('owner_name', 'House Owner')
    location = data.get('house_location', 'Andhra Pradesh, India')
    month_usage = float(data.get('month_usage_kwh', 0))
    grid_import = float(data.get('grid_import_kwh', 0))
    grid_export = float(data.get('grid_export_kwh', 0))
    
    # --- APSPDCL BILLING CALCULATION ---
    bill = calculate_ap_bill(grid_import, grid_export)
    units = grid_import
    
    energy_charge = bill['energy_charge']
    fixed_charge = bill['fixed_charge']
    customer_charge = bill['customer_charge']
    ed_duty = bill['ed_duty']
    fsa_charge = bill['fsa_charge']
    export_credit = bill['export_credit']
    total_current = bill['total_current']
    net_bill_amount = bill['final_bill']
    
    bill_date = datetime.datetime.now().strftime('%d-%b-%Y')
    due_date = (datetime.datetime.now() + datetime.timedelta(days=15)).strftime('%d-%b-%Y')
    bill_month = datetime.datetime.now().strftime('%B %Y')

    # --- PDF GENERATION ---
    class BillPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'SOUTHERN POWER DISTRIBUTION COMPANY OF A.P. LTD.', 0, 1, 'C')
            self.set_font('Arial', '', 12)
            self.cell(0, 10, '(APSPDCL - AP BOARD)', 0, 1, 'C')
            self.ln(5)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)

        def footer(self):
            self.set_y(-25)
            self.set_font('Arial', 'I', 8)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(2)
            self.cell(0, 10, 'This is a computer-generated energy statement. Pay via SPDCL portal or authorized centers.', 0, 0, 'C')

    pdf = BillPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Bill Info Header
    pdf.set_font('Arial', 'B', 11)
    col_width = 95
    line_height = 6
    
    y0 = pdf.get_y()
    pdf.cell(col_width, line_height, f"BILL NO: {datetime.datetime.now().strftime('%Y%j%H%M')}", 0, 0)
    pdf.cell(col_width, line_height, f"DATE: {bill_date}", 0, 1, 'R')
    pdf.cell(col_width, line_height, f"MONTH: {bill_month.upper()}", 0, 0)
    pdf.cell(col_width, line_height, f"DUE DATE: {due_date}", 0, 1, 'R')
    pdf.ln(4)
    
    # Consumer Details Section
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " CONSUMER DETAILS", 0, 1, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(2)
    
    details = [
        ("Service No", meter),
        ("Name", owner_name.upper()),
        ("Address", location.upper()),
        ("Category", "LT-I(A) DOMESTIC"),
        ("Contract Load", "3.00 KW")
    ]
    
    for label, val in details:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, line_height, f"{label}:", 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, line_height, str(val), 0, 1)
    
    pdf.ln(5)

    # Consumption Details
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " METER READING & CONSUMPTION", 0, 1, 'L', True)
    pdf.set_font('Arial', '', 10)
    pdf.ln(2)
    
    consumption = [
        ("Prev Reading", f"{(month_usage * 0.8):.2f}"),
        ("Curr Reading", f"{(month_usage * 0.8 + units):.2f}"),
        ("Total Units", f"{units:.2f} kWh"),
        ("Net Units", f"{units:.2f} (After Solar Adjustment)")
    ]
    
    for label, val in consumption:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, line_height, f"{label}:", 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, line_height, str(val), 0, 1)

    pdf.ln(5)

    # Charges Breakdown Table
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, " CHARGES BREAKDOWN (All amounts in INR)", 0, 1, 'L', True)
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(140, 8, "Description", 1)
    pdf.cell(50, 8, "Amount (Rs.)", 1, 1, 'R')
    
    pdf.set_font('Arial', '', 10)
    charges = [
        ("1. Energy Charges (Slab Wise)", energy_charge),
        ("2. Fixed/Demand Charges", fixed_charge),
        ("3. Customer Charges", customer_charge),
        ("4. Electricity Duty (ED)", ed_duty),
        ("5. FSA / Fuel Surcharge", fsa_charge),
    ]
    
    for desc, amt in charges:
        pdf.cell(140, 7, desc, 1)
        pdf.cell(50, 7, f"{amt:.2f}", 1, 1, 'R')
        
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(140, 8, "Gross Current Month Charges", 1)
    pdf.cell(50, 8, f"{total_current:.2f}", 1, 1, 'R')
    
    pdf.set_text_color(200, 0, 0) # Red for credits
    pdf.cell(140, 8, "Solar Export Credit (-ve)", 1)
    pdf.cell(50, 8, f"- {export_credit:.2f}", 1, 1, 'R')
    pdf.set_text_color(0, 0, 0) # Back to black
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(230, 240, 255)
    pdf.cell(140, 10, "NET AMOUNT PAYABLE (TOTAL)", 1, 0, 'L', True)
    pdf.cell(50, 10, f"Rs. {net_bill_amount:.2f}", 1, 1, 'R', True)
    
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, f"AMOUNT IN WORDS: Rupees {net_bill_amount:,.0f} only.", 0, 1)

    # Return PDF response
    response_out = pdf.output(dest='S')
    
    return Response(
        response_out,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=AP_Board_Bill_{meter}.pdf"}
    )

@app.route('/api/simulation/toggle_grid', methods=['POST'])
def toggle_grid():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    new_state = sim.toggle_grid()
    print(f"DEBUG: Grid Toggled for {email}. New State: {new_state}")
    
    return jsonify({
        "success": True, 
        "grid_online": new_state,
        "message": f"Grid is now {'ONLINE' if new_state else 'OFFLINE (Island Mode)'}"
    })

@app.route('/api/upload_data', methods=['POST'])
def upload_data():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"})
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"})
        
    if file:
        try:
            # UNIQUE UPLOAD PATH: Fixes Data Race Drawback
            import uuid
            email_safe = session['user_email'].replace("@", "_").replace(".", "_")
            upload_id = str(uuid.uuid4())[:8]
            filename = f"{email_safe}_{upload_id}_{file.filename}"
            
            # Ensure uploads directory exists
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            # Reload sim with new data
            email = (session['user_email'] or '').strip().lower()
            sim = get_sim(email)
            
            # Use the absolute filepath to load data
            # Robust Validation
            import pandas as pd
            try:
                df = pd.read_csv(filepath)
                required_cols = ["load_kW", "solar_kW", "price_per_MWh"]
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    if os.path.exists(filepath): os.remove(filepath)
                    return jsonify({"success": False, "message": f"Invalid dataset. Missing required columns: {', '.join(missing)}"}), 400
                
                # Sanity check values - ensure no nulls in critical columns
                if df['load_kW'].isnull().any() or df['solar_kW'].isnull().any() or df['price_per_MWh'].isnull().any():
                     if os.path.exists(filepath): os.remove(filepath)
                     return jsonify({"success": False, "message": "Dataset contains null values in critical columns (load_kW, solar_kW, or price_per_MWh)."}), 400
                     
            except Exception as e:
                if os.path.exists(filepath): os.remove(filepath)
                return jsonify({"success": False, "message": f"File parsing error: {str(e)}"}), 400

            success = sim.load_data(filepath, original_filename=file.filename)
            print(f"DEBUG: load_data returned {success}. Rows: {len(sim.df) if sim.df is not None else 0}")
            
            # The new validation above handles parsing errors and missing columns,
            # so this specific check might be redundant or need adjustment based on sim.load_data's return.
            # Keeping it for now as per instruction, but it might always be true if validation passes.
            if not success:
                return jsonify({"success": False, "message": "Failed to parse CSV file. Ensure it has required columns: load_kW, solar_kW, price_per_MWh"}), 400
                
            sim.reset() # Reset simulation state with new data
            print(f"DEBUG: sim.df is {'SET' if sim.df is not None else 'NONE'} after reset")
            
            return jsonify({
                "success": True, 
                "message": f"Data loaded successfully. ({len(sim.df)} rows)",
                "benchmark_savings": getattr(sim, 'benchmark_savings', 0.0),
                "dataset": sim.dataset_name
            })
        except Exception as e:
            import traceback
            print(f"ERROR in upload_data: {e}")
            return jsonify({"success": False, "message": f"Internal server error during upload: {str(e)}"}), 500

@app.route('/api/export_telemetry', methods=['GET'])
def export_telemetry():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    if not sim.results:
        return jsonify({"success": False, "message": "No telemetry data to export."}), 400
        
    import csv
    import io
    from flask import Response
    
    output = io.StringIO()
    # We take the keys from the first result as the CSV header
    keys = sim.results[0].keys()
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    writer.writerows(sim.results)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=telemetry_data.csv"}
    )

@app.route('/api/email_telemetry', methods=['POST'])
def email_telemetry():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    target_email = data.get('email_address') if data else None
    
    if not target_email:
        return jsonify({"success": False, "message": "Target email address is required."}), 400

    email = (session['user_email'] or '').strip().lower()
    sim = get_sim(email)
    
    if not sim.results:
        return jsonify({"success": False, "message": "No telemetry data to export."}), 400
        
    import csv
    import io
    
    output = io.StringIO()
    # We take the keys from the first result as the CSV header
    keys = sim.results[0].keys()
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    writer.writerows(sim.results)
    
    csv_content = output.getvalue()
    
    # --- ACTUAL EMAIL SENDING (SMTP) ---
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email import encoders
    
    # =====================================================================
    # Users should provide their Gmail credentials in the Settings page.
    # =====================================================================
    # Use environment variables first, then fallback to user settings in DB
    user_settings = db.get_user_settings(session['user_email'])
    SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL") or user_settings.get("sender_email")
    SENDER_PASSWORD = os.getenv("SMTP_SENDER_PASSWORD") or user_settings.get("sender_password")
    
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return jsonify({
            "success": False, 
            "message": "Error: Check server configuration. You must enter your Gmail credentials in the Settings page to enable sending."
        }), 500

    try:
        # Construct the email message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = target_email
        msg['Subject'] = "Microgrid OS - Exported Telemetry Data"

        body = "Attached is the latest simulation data exported from Microgrid OS."
        msg.attach(MIMEText(body, 'plain'))

        # Attach the CSV file
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(csv_content.encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="telemetry_data.csv"')
        msg.attach(part)

        # Connect to Gmail SMTP server and send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, target_email, text)
        server.quit()

        return jsonify({
            "success": True, 
            "message": f"Successfully sent telemetry data to {target_email}!"
        })
    except Exception as e:
        print(f"SMTP Error: {e}")
        return jsonify({
            "success": False, 
            "message": f"Failed to send email. Ensure App Password is correct. Error: {str(e)}"
        }), 500

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    email = (session['user_email'] or '').strip().lower()
    if email in simulations:
        # Re-initialize the simulation engine instance for this user
        from backend.simulation_engine import SimulationEngine
        simulations[email] = SimulationEngine()
    
    return jsonify({"success": True, "message": "Simulation cache cleared successfully."})

@app.route('/about')
def about():
    if 'user_email' not in session:
        return redirect(url_for('index'))
    return render_template('about.html', email=session['user_email'])


@app.route('/api/house/dashboard', methods=['GET'])
def house_dashboard_api():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    import random
    
    # Use consumer number from session; fall back to query param
    meter = session.get('consumer_number')
    if not meter:
        meter = request.args.get('consumer_id', '').strip() or request.args.get('meter', '').strip()
        
    if not meter:
        return jsonify({"success": False, "message": "No consumer number found. Please complete setup."}), 400
    
    # Validate meter: must be numeric and 6-12 digits
    if not meter.isdigit() or not (6 <= len(meter) <= 12):
        return jsonify({"success": False, "message": "Invalid consumer number. Must be 6–12 digits."}), 400
    
    # SECURITY REFINE: Check Ownership
    email = session.get('user_email')
    # If explicitly searching by ID, verify transparency/ownership
    query_id = request.args.get('consumer_id') or request.args.get('meter')
    if query_id and not db.check_meter_ownership(email, meter):
         return jsonify({"success": False, "message": "Unauthorized: You do not have permission to view this meter's data."}), 403
    
    # Fetch from Database (Scalable)
    data = db.get_house_data(meter)
    if not data:
        return jsonify({"success": False, "message": "Consumer not found in records. (Redirecting to setup...)"}), 404
    
    # Map CSV columns to JSON response
    # --- Usage ---
    today_usage  = float(data.get('today_usage_kwh', 0))
    week_usage   = float(data.get('week_usage_kwh', 0))
    month_usage  = float(data.get('month_usage_kwh', 0))
    
    # --- Solar ---
    solar_today  = float(data.get('solar_generated_today', 0))
    solar_month  = float(data.get('solar_generated_month', 0))
    solar_contribution = round((solar_today / today_usage) * 100, 1) if today_usage else 0
    solar_contribution = min(solar_contribution, 95.0)  # Cap at 95%
    
    # --- Grid ---
    grid_import  = float(data.get('grid_import_kwh', 0))
    grid_export  = float(data.get('grid_export_kwh', 0))
    price_per_unit = float(data.get('electricity_price', 6.0))
    feed_in_tariff = float(data.get('feed_in_tariff', 4.0))
    
    # --- APSPDCL Shared Billing Logic ---
    bill = calculate_ap_bill(grid_import, grid_export)
    
    import_cost   = bill['total_current']
    export_credit = bill['export_credit']
    final_bill    = bill['final_bill']
    
    # --- Savings ---
    baseline_usage    = float(data.get('baseline_usage', today_usage + 2.0))
    electricity_saved = float(data.get('baseline_usage', baseline_usage) - data.get('optimized_usage', today_usage))
    money_saved       = round(electricity_saved * price_per_unit, 2)
    
    # --- Solar Subsidy ---
    capacity_kw = int(data.get('solar_capacity_kw', 1))
    subsidy_amount = float(data.get('subsidy_amount', 0))
    
    # --- Price Prediction (Keep seeded simulation for 24h curve) ---
    seed = abs(hash(meter)) % (2**31)
    base_curve = [2.8, 2.7, 2.6, 2.5, 2.6, 2.9, 3.5, 4.2, 5.0, 5.5, 5.8, 6.0, 6.2, 6.1, 5.8, 5.6, 6.0, 7.2, 7.8, 8.1, 7.5, 6.2, 5.0, 3.5]
    price_prediction = []
    random.seed(seed + 1)
    for h, base in enumerate(base_curve, 1):
        noise = random.uniform(-0.3, 0.3)
        price_prediction.append({"hour": h, "price_rs": round(base + noise, 2)})
    
    # --- Due date from CSV or calc ---
    bill_due_date = str(data.get('bill_due_date', '2026-04-01'))
    
    # --- Last Month Prediction (Randomized for demo) ---
    random.seed(seed + 2)
    last_month_usage = round(month_usage * random.uniform(0.9, 1.1), 1)
    last_month_solar = round(solar_month * random.uniform(0.85, 1.15), 1)
    last_month_savings = round(last_month_solar * price_per_unit * 0.8, 2)
    last_month_bill = round(max((last_month_usage * price_per_unit) - (last_month_solar * feed_in_tariff), 0), 2)
    
    # Fetch payment status from DB
    user = db.find_user(email)
    payment_status = user.get("last_payment_status", "UNPAID")
    
    return jsonify({
        "success": True,
        "meter": meter,
        "owner_name": data.get('owner_name', 'House Owner'),
        "location": data.get('house_location', 'N/A'),
        "usage": {
            "today":  today_usage,
            "week":   week_usage,
            "month":  month_usage
        },
        "solar": {
            "today":                solar_today,
            "month":               solar_month,
            "contribution_percent": solar_contribution,
            "grid_percent":         round(100 - solar_contribution, 1)
        },
        "grid": {
            "import_kwh":   grid_import,
            "export_kwh":   grid_export,
            "import_cost":  import_cost,
            "export_credit": export_credit,
            "final_bill":   final_bill
        },
        "savings": {
            "electricity_saved": electricity_saved,
            "money_saved":       money_saved,
            "baseline_usage":    baseline_usage,
            "optimized_usage":   float(data.get('optimized_usage', today_usage))
        },
        "subsidy": {
            "capacity_kw":    capacity_kw,
            "subsidy_amount": subsidy_amount,
            "scheme":         "PM Surya Ghar: Muft Bijli Yojana"
        },
        "price_prediction": price_prediction,
        "bill": {
            "grid_import_cost": import_cost,
            "export_credit":    export_credit,
            "final_bill":       final_bill,
            "due_date":         bill_due_date
        },
        "last_month_predicted": {
            "usage_kwh": last_month_usage,
            "solar_kwh": last_month_solar,
            "savings_rs": last_month_savings,
            "bill_rs": last_month_bill
        },
        "payment_status": payment_status
    })

@app.route('/api/house/pay_bill', methods=['POST'])
def api_pay_bill():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.json
    meter = data.get('meter')
    amount = data.get('amount')
    
    if not meter or not amount:
        return jsonify({"success": False, "message": "Missing payment details."}), 400
        
    # Verify ownership before allowing payment record
    if not db.check_meter_ownership(session['user_email'], meter):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    success = db.record_payment(
        session['user_email'], 
        meter, 
        amount, 
        datetime.datetime.now().strftime("%B %Y")
    )
    
@app.route('/api/house/export_telemetry', methods=['GET'])
def house_telemetry_export():
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    meter = session.get('consumer_number')
    if not meter:
        meter = request.args.get('consumer_id', '').strip() or request.args.get('meter', '').strip()
        
    if not meter:
        return jsonify({"success": False, "message": "No consumer number found."}), 400

    # Ownership check
    email = session.get('user_email')
    if not db.check_meter_ownership(email, meter):
         return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = db.get_house_data(meter)
    if not data:
        return jsonify({"success": False, "message": "Data not found."}), 404

    import csv
    import io
    import random
    from flask import Response

    today_usage = float(data.get('today_usage_kwh', 0))
    solar_today = float(data.get('solar_generated_today', 0))
    price_per_unit = float(data.get('electricity_price', 6.0))

    seed = abs(hash(meter)) % (2**31)
    random.seed(seed)

    # Standard 24h distributions
    # Usage: Typical residential double-peak (morning and evening)
    usage_dist = [0.02, 0.01, 0.01, 0.01, 0.02, 0.04, 0.06, 0.07, 0.05, 0.04, 0.03, 0.03, 
                  0.04, 0.03, 0.03, 0.04, 0.05, 0.07, 0.09, 0.10, 0.08, 0.05, 0.03, 0.02]
    
    # Solar: Bell curve peaking at noon
    solar_dist = [0, 0, 0, 0, 0, 0, 0.02, 0.08, 0.12, 0.15, 0.18, 0.18, 
                  0.15, 0.08, 0.04, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Hour", "Usage_kWh", "Solar_Generation_kWh", "Grid_Import_kWh", "Grid_Export_kWh", "Price_Rs_kWh"])

    for h in range(24):
        # Calculate hourly values with some random noise
        h_usage = today_usage * usage_dist[h] * random.uniform(0.9, 1.1)
        h_solar = solar_today * solar_dist[h] * random.uniform(0.95, 1.05)
        
        # Energy balance
        if h_solar >= h_usage:
            grid_import = 0
            grid_export = h_solar - h_usage
        else:
            grid_import = h_usage - h_solar
            grid_export = 0
            
        # Price curve (consistent with dashboard)
        base_prices = [2.8, 2.7, 2.6, 2.5, 2.6, 2.9, 3.5, 4.2, 5.0, 5.5, 5.8, 6.0, 
                       6.2, 6.1, 5.8, 5.6, 6.0, 7.2, 7.8, 8.1, 7.5, 6.2, 5.0, 3.5]
        h_price = round(base_prices[h] + random.uniform(-0.1, 0.1), 2)

        writer.writerow([
            f"{h:02d}:00",
            round(h_usage, 3),
            round(h_solar, 3),
            round(grid_import, 3),
            round(grid_export, 3),
            h_price
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=telemetry_{meter}.csv"}
    )
    return response

if __name__ == '__main__':
    # Use Waitress for Production-ready server (No Warnings)
    from waitress import serve
    print("✅ Server Started on http://127.0.0.1:5001")
    print("🚀 App is running in PRODUCTION mode.")
    serve(app, host='0.0.0.0', port=5001)
