
import os
import Queue
import sys
import uuid
from flask import Flask
from flask import request
from flask import make_response
from jinja2 import Environment, FileSystemLoader
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import threading
import naarad.naarad_constants as CONSTANTS
import naarad.resources
from naarad import Naarad
from naarad.webapp.circular_buffer import CircularBuffer

template_loader = FileSystemLoader(naarad.resources.get_dir())
template_environment = Environment(loader=template_loader)
header_template_data= { 'custom_stylesheet_includes' : CONSTANTS.STYLESHEET_INCLUDES,
                          'custom_javascript_includes' : CONSTANTS.JAVASCRIPT_INCLUDES,
                          'resource_path': CONSTANTS.RESOURCES_PATH }
tbd = Queue.Queue()
recent_analysis = CircularBuffer(size=10)
queued_analysis = {}

def worker():
  while True:
    sessionid = tbd.get()
    queued_analysis[sessionid] = 'Processing'
    Naarad().analyze(os.path.join('/tmp/analysis',sessionid), os.path.join(os.path.join('/tmp/analysis',sessionid),'report'), config=os.path.join(os.path.join('/tmp/analysis',sessionid),'config-gc'))
    recent_analysis.append(sessionid)
    queued_analysis.pop(sessionid)
    tbd.task_done()

for i in range(10):
  t = threading.Thread(target=worker)
  t.daemon = True
  t.start()

app = Flask(__name__, static_folder='../resources')
@app.route('/')
def landing_page():
  if request.cookies.get('sessionid'):
    sessionid = request.cookies.get('sessionid').encode('ascii', 'ignore')
  else:
    sessionid = get_sessionid()
  response_html = template_environment.get_template(CONSTANTS.TEMPLATE_HEADER).render(**header_template_data)
  response_html += template_environment.get_template(CONSTANTS.TEMPLATE_LANDING_PAGE).render(recent_analysis=recent_analysis, queued_analysis=queued_analysis)
  response_html += template_environment.get_template(CONSTANTS.TEMPLATE_FOOTER).render(session_id=sessionid)
  response = make_response(response_html)
  if not request.cookies.get('sessionid'):
    response.set_cookie('sessionid', sessionid)
  return response

@app.route('/analyze', methods= ['GET', 'POST'])
def upload_file():
  if request.cookies.get('sessionid'):
    sessionid = request.cookies.get('sessionid').encode('ascii', 'ignore')
  else:
    sessionid = get_sessionid()
  if request.method == 'POST':
    if not os.path.exists(os.path.join('/tmp/analysis/',sessionid)):
      os.makedirs(os.path.join('/tmp/analysis/',sessionid))
    for file_name in request.files.getlist('file[]'):
      file_name.save(os.path.join(os.path.join('/tmp/analysis/',sessionid),file_name.filename))
    tbd.put(sessionid)
    queued_analysis[sessionid] = 'Queued'

  response_html = template_environment.get_template(CONSTANTS.TEMPLATE_HEADER).render(**header_template_data)
  response_html += template_environment.get_template(CONSTANTS.TEMPLATE_ANALYZE_PAGE).render()
  response_html += template_environment.get_template(CONSTANTS.TEMPLATE_FOOTER).render(session_id=sessionid)
  response = make_response(response_html)
  if not request.cookies.get('sessionid'):
    response.set_cookie('sessionid', sessionid)
  return response, 200

@app.route('/view')
def view_report_page():
  if request.cookies.get('sessionid'):
    sessionid = request.cookies.get('sessionid').encode('ascii', 'ignore')
  else:
    sessionid = get_sessionid()
  if request.method == 'POST':
    for file_name in request.files.keys():
      f = request.files[file_name]
      f.save ('/tmp/analysis/' + sessionid + '/' + file_name)
  else:
    response_html = template_environment.get_template(CONSTANTS.TEMPLATE_HEADER).render(**header_template_data)
    response_html += template_environment.get_template(CONSTANTS.TEMPLATE_VIEWREPORT_PAGE).render()
    response_html += template_environment.get_template(CONSTANTS.TEMPLATE_FOOTER).render(session_id=sessionid)
    response = make_response(response_html)
    if not request.cookies.get('sessionid'):
      response.set_cookie('sessionid', sessionid)
  return response

@app.route('/view/<report_id>')
def view_report(report_id):
  return 'Report : ' + report_id

@app.route('/api')
@app.route('/api/signal_start')
@app.route('/api/signal_stop')
@app.route('/api/analyze')
@app.route('/api/diff')
def api_tbd():
  return 'Not implemented'

def get_sessionid():
  return str(uuid.uuid4())

if __name__ == "__main__":
  app.run(host='0.0.0.0')
