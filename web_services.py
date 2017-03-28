from datetime import datetime
from flask import Flask, request, flash, url_for, redirect, \
     render_template, abort, send_from_directory, json, Response, jsonify, make_response, send_from_directory
import psycopg2

app = Flask(__name__)
app.config.from_pyfile('flaskapp.cfg')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route("/ndvist/aoicheck/<float:xmin>/<float:ymin>/<float:xmax>/<float:ymax>", methods=['GET'])
def aoi_check(xmin, ymin, xmax, ymax):
    conn = psycopg2.connect(database=os.environ['OPENSHIFT_APP_NAME'], user=os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'], 
	        password=os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'], host=os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'], 
	        port=os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'] )
    cursor = conn.cursor()
    sql = "SELECT ST_Contains(a.geometry, ST_Transform(ST_MakeEnvelope(%f, %f, %f, %f, 4326),32635)) FROM ndvist.project_area a" % (xmin, ymin, xmax, ymax)
    cursor.execute(sql)
    result = cursor.fetchone()

    if result[0] == True:
        json_data = []
        hop = {'status': u"inAOI"}
        json_data.append(hop)

        return Response(json.dumps(json_data, ensure_ascii=False),  mimetype='application/json; charset=utf8')

    else:
        json_data = []
        hop = {'status': u"outAOI"}
        json_data.append(hop)

        return Response(json.dumps(json_data, ensure_ascii=False),  mimetype='application/json; charset=utf8')

@app.route("/ndvist/ndvivalue/<float:x>/<float:y>/<int:date>", methods=['GET'])
def ndvi_value(x, y, date):
    conn = psycopg2.connect(database=os.environ['OPENSHIFT_APP_NAME'], user=os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'], 
	        password=os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'], host=os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'], 
	        port=os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'] )
    cursor = conn.cursor()
    sql = "SELECT ST_Value(rast, ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), 32635)) FROM ndvist.ndvi_%i WHERE ST_Intersects(rast, ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), 32635))" % (x, y, date, x, y)
    cursor.execute(sql)
    result = cursor.fetchone()
    json_data = []
    hop = {'ndviValue': result[0]}
    json_data.append(hop)

    return Response(json.dumps(json_data, ensure_ascii=False),  mimetype='application/json; charset=utf8')

@app.route('/<path:resource>')
def serveStaticResource(resource):
    return send_from_directory('static/', resource)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'Error': 'Not Found'}), 404)

if __name__ == '__main__':
    app.run()
