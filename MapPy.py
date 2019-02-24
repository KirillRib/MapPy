from flask import Flask
from flask import render_template
from flask import send_file
from flask import request

app = Flask(__name__)


@app.route("/")
def output():
	return render_template("index.html", name="Joe")



@app.route('/get_image')
def get_image():
    with open("test.png", 'rb') as bites:
        return send_file(
                     io.BytesIO(bites.read()),
                     attachment_filename='test.png',
                     mimetype='test/png'
               )

@app.route('/file-downloads/')
def file_downloads():
	try:
		return render_template('downloads.html')
	except Exception as e:
		return str(e)
	

@app.route('/return-files/')
def return_files_tut():
	try:
		print(request.args.get('x'), request.args.get('y'), request.args.get('z'))
		return send_file('test.png', attachment_filename='test.png')
	except Exception as e:
		return str(e)

if __name__ == "__main__":
	app.run()