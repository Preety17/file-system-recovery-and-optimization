from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from main import FileSystemManager  # Import your existing class

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize the file system manager
fs = FileSystemManager("virtual_fs")

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Get basic stats
    stats = fs.analyze_performance()
    # Get root directory contents
    root_contents = fs.list_directory('/')
    return render_template('dashboard.html', stats=stats, contents=root_contents)

@app.route('/browse/<path:dir_path>')
def browse_directory(dir_path):
    full_path = '/' + dir_path
    contents = fs.list_directory(full_path)
    if not contents:
        flash(f"Directory {full_path} not found", 'error')
        return redirect(url_for('dashboard'))
    return render_template('browse.html', contents=contents, current_path=full_path)

@app.route('/create_file', methods=['POST'])
def create_file():
    path = request.form.get('path')
    content = request.form.get('content', '')
    
    if not path:
        flash("Path is required", 'error')
        return redirect(url_for('dashboard'))
    
    if fs.create_file(path, content):
        flash("File created successfully", 'success')
    else:
        flash("Failed to create file", 'error')
    
    return redirect(url_for('browse_directory', dir_path=os.path.dirname(path.lstrip('/'))))

@app.route('/create_directory', methods=['POST'])
def create_directory():
    path = request.form.get('path')
    
    if not path:
        flash("Path is required", 'error')
        return redirect(url_for('dashboard'))
    
    if fs.create_directory(path):
        flash("Directory created successfully", 'success')
    else:
        flash("Failed to create directory", 'error')
    
    return redirect(url_for('browse_directory', dir_path=os.path.dirname(path.lstrip('/'))))

@app.route('/read_file/<path:file_path>')
def read_file(file_path):
    full_path = '/' + file_path
    content = fs.read_file(full_path)
    
    if content is None:
        flash("File not found or could not be read", 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('file_view.html', 
                         file_path=full_path, 
                         content=content,
                         parent_dir=os.path.dirname(full_path))

@app.route('/write_file', methods=['POST'])
def write_file():
    path = request.form.get('path')
    content = request.form.get('content', '')
    
    if not path:
        flash("Path is required", 'error')
        return redirect(url_for('dashboard'))
    
    if fs.write_file(path, content):
        flash("File saved successfully", 'success')
    else:
        flash("Failed to save file", 'error')
    
    return redirect(url_for('read_file', file_path=path.lstrip('/')))

@app.route('/delete_file', methods=['POST'])
def delete_file():
    path = request.form.get('path')
    
    if not path:
        flash("Path is required", 'error')
        return redirect(url_for('dashboard'))
    
    parent_dir = os.path.dirname(path)
    
    if fs.delete_file(path):
        flash("File deleted successfully", 'success')
    else:
        flash("Failed to delete file", 'error')
    
    return redirect(url_for('browse_directory', dir_path=parent_dir.lstrip('/')))

@app.route('/delete_directory', methods=['POST'])
def delete_directory():
    path = request.form.get('path')
    recursive = request.form.get('recursive', 'false') == 'true'
    
    if not path:
        flash("Path is required", 'error')
        return redirect(url_for('dashboard'))
    
    parent_dir = os.path.dirname(path)
    
    if fs.delete_directory(path, recursive):
        flash("Directory deleted successfully", 'success')
    else:
        flash("Failed to delete directory", 'error')
    
    return redirect(url_for('browse_directory', dir_path=parent_dir.lstrip('/')))

@app.route('/defragment')
def defragment():
    if fs.defragment():
        flash("Defragmentation completed successfully", 'success')
    else:
        flash("Defragmentation failed", 'error')
    return redirect(url_for('dashboard'))

@app.route('/recover_metadata')
def recover_metadata():
    try:
        fs._recover_metadata()
        flash("Metadata recovery completed", 'success')
    except Exception as e:
        flash(f"Recovery failed: {str(e)}", 'error')
    return redirect(url_for('dashboard'))

@app.route('/simulate_crash/<crash_type>')
def simulate_crash(crash_type):
    if crash_type in ['metadata', 'files']:
        fs.simulate_disk_crash(crash_type)
        flash(f"Simulated {crash_type} corruption", 'warning')
    else:
        flash("Invalid crash type", 'error')
    return redirect(url_for('dashboard'))

@app.route('/api/performance')
def api_performance():
    return jsonify(fs.analyze_performance())

if __name__ == '__main__':
    app.run(debug=True)