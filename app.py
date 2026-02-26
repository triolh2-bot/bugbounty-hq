"""
BugBountyHQ - Bug Bounty Program Management Platform
A SaaS for managing bug bounty programs, VDPs, and vulnerability disclosure.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import json
import sqlite3
import uuid
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bugbounty-secret-key-change-me')

# Database setup
DB_NAME = 'bugbounty.db'

def init_db():
    """Initialize database with tables"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Programs table
    c.execute('''CREATE TABLE IF NOT EXISTS programs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        scope TEXT,
        rules TEXT,
        bounty_range TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Submissions table
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
        id TEXT PRIMARY KEY,
        program_id TEXT,
        researcher TEXT,
        title TEXT,
        description TEXT,
        severity TEXT,
        status TEXT DEFAULT 'submitted',
        bounty REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (program_id) REFERENCES programs (id)
    )''')
    
    # Researchers table
    c.execute('''CREATE TABLE IF NOT EXISTS researchers (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        reputation INTEGER DEFAULT 0,
        bugs_found INTEGER DEFAULT 0,
        total_earnings REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# ============== Routes ==============

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get stats
    c.execute('SELECT COUNT(*) as count FROM programs')
    programs_count = c.fetchone()['count']
    
    c.execute('SELECT COUNT(*) as count FROM submissions')
    submissions_count = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) as count FROM submissions WHERE status = 'resolved'")
    resolved_count = c.fetchone()['count']
    
    c.execute('SELECT SUM(bounty) as total FROM submissions WHERE bounty IS NOT NULL')
    total_paid = c.fetchone()['total'] or 0
    
    # Recent submissions
    c.execute('''SELECT s.*, p.name as program_name 
                 FROM submissions s 
                 LEFT JOIN programs p ON s.program_id = p.id 
                 ORDER BY s.created_at DESC LIMIT 10''')
    recent = c.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                           programs_count=programs_count,
                           submissions_count=submissions_count,
                           resolved_count=resolved_count,
                           total_paid=total_paid,
                           recent=recent)

# ============== Program Routes ==============

@app.route('/programs')
def programs():
    """List all programs"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM programs ORDER BY created_at DESC')
    programs = c.fetchall()
    conn.close()
    return render_template('programs.html', programs=programs)

@app.route('/programs/new', methods=['GET', 'POST'])
def new_program():
    """Create new program"""
    if request.method == 'POST':
        data = request.form
        program_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO programs (id, name, description, scope, rules, bounty_range)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (program_id, data['name'], data['description'], 
                   data['scope'], data['rules'], data.get('bounty_range', '')))
        conn.commit()
        conn.close()
        
        return redirect(url_for('programs'))
    
    return render_template('program_form.html', program=None)

@app.route('/programs/<program_id>')
def program_detail(program_id):
    """Program detail page"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM programs WHERE id = ?', (program_id,))
    program = c.fetchone()
    
    if program:
        c.execute('''SELECT * FROM submissions 
                     WHERE program_id = ? 
                     ORDER BY created_at DESC''', (program_id,))
        submissions = c.fetchall()
    else:
        submissions = []
    
    conn.close()
    return render_template('program_detail.html', program=program, submissions=submissions)

# ============== Submission Routes ==============

@app.route('/submissions')
def submissions():
    """List all submissions"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT s.*, p.name as program_name 
                 FROM submissions s 
                 LEFT JOIN programs p ON s.program_id = p.id 
                 ORDER BY s.created_at DESC''')
    submissions = c.fetchall()
    conn.close()
    return render_template('submissions.html', submissions=submissions)

@app.route('/submissions/new', methods=['GET', 'POST'])
def new_submission():
    """Submit new vulnerability"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.form
        submission_id = str(uuid.uuid4())
        
        c.execute('''INSERT INTO submissions 
                     (id, program_id, researcher, title, description, severity)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (submission_id, data['program_id'], data['researcher'],
                   data['title'], data['description'], data['severity']))
        conn.commit()
        conn.close()
        
        return redirect(url_for('submissions'))
    
    # Get programs for dropdown
    c.execute('SELECT id, name FROM programs')
    programs = c.fetchall()
    conn.close()
    
    return render_template('submission_form.html', programs=programs)

@app.route('/submissions/<submission_id>', methods=['GET', 'POST'])
def submission_detail(submission_id):
    """Submission detail and update"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.form
        c.execute('''UPDATE submissions 
                     SET status = ?, severity = ?, bounty = ?
                     WHERE id = ?''',
                  (data['status'], data['severity'], 
                   float(data['bounty']) if data['bounty'] else None,
                   submission_id))
        conn.commit()
    
    c.execute('''SELECT s.*, p.name as program_name 
                 FROM submissions s 
                 LEFT JOIN programs p ON s.program_id = p.id 
                 WHERE s.id = ?''', (submission_id,))
    submission = c.fetchone()
    conn.close()
    
    return render_template('submission_detail.html', submission=submission)

# ============== Researcher Routes ==============

@app.route('/researchers')
def researchers():
    """List researchers"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM researchers ORDER BY reputation DESC')
    researchers = c.fetchall()
    conn.close()
    return render_template('researchers.html', researchers=researchers)

# ============== API Routes ==============

@app.route('/api/programs', methods=['GET'])
def api_programs():
    """API: List programs"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM programs')
    programs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(programs)

@app.route('/api/programs', methods=['POST'])
def api_create_program():
    """API: Create program"""
    data = request.json
    program_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO programs (id, name, description, scope, rules, bounty_range)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (program_id, data.get('name'), data.get('description'),
               data.get('scope'), data.get('rules'), data.get('bounty_range')))
    conn.commit()
    conn.close()
    
    return jsonify({'id': program_id, 'success': True})

@app.route('/api/submissions', methods=['GET'])
def api_submissions():
    """API: List submissions"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''SELECT s.*, p.name as program_name 
                 FROM submissions s 
                 LEFT JOIN programs p ON s.program_id = p.id 
                 ORDER BY s.created_at DESC''')
    submissions = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(submissions)

@app.route('/api/submissions', methods=['POST'])
def api_create_submission():
    """API: Create submission"""
    data = request.json
    submission_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT INTO submissions 
                 (id, program_id, researcher, title, description, severity)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (submission_id, data.get('program_id'), data.get('researcher'),
               data.get('title'), data.get('description'), data.get('severity')))
    conn.commit()
    conn.close()
    
    return jsonify({'id': submission_id, 'success': True})

@app.route('/api/stats')
def api_stats():
    """API: Get stats"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM programs')
    programs = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM submissions')
    submissions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM submissions WHERE status = 'resolved'")
    resolved = c.fetchone()[0]
    
    c.execute('SELECT SUM(bounty) FROM submissions WHERE bounty IS NOT NULL')
    total_paid = c.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'programs': programs,
        'submissions': submissions,
        'resolved': resolved,
        'total_paid': total_paid
    })

# ============== Webhooks ==============

@app.route('/webhook/hackerone', methods=['POST'])
def webhook_hackerone():
    """Handle HackerOne webhooks"""
    data = request.json
    # Process HackerOne submission
    # Map to our format
    return jsonify({'received': True})

@app.route('/webhook/bugcrowd', methods=['POST'])
def webhook_bugcrowd():
    """Handle Bugcrowd webhooks"""
    data = request.json
    # Process Bugcrowd submission
    return jsonify({'received': True})

# ============== Health ==============

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'features': [
            'Program Management',
            'Submission Tracking',
            'Researcher Portal',
            'API Access',
            'Webhook Integration'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🔓 BugBountyHQ running on http://localhost:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')
