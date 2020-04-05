import cherrypy
import os
import os.path
import sqlite3
import pandas as pd
import pyqrcode

DB_STRING = 'database.db'

class Final_app:

    @cherrypy.expose
    def test(self):
        return read_html_file("test.html")

    ## HOME PAGE

    @cherrypy.expose
    def index(self):
        return read_html_file("home_page.html")


    ## COLLECTION PAGE & SUPPORT FUNCTIONS

    @cherrypy.expose
    def collection(self):
        return read_html_file("collection_page.html") % create_table()

    ## UPDATE PAGE
    @cherrypy.expose
    def update(self,update):

        with sqlite3.connect(DB_STRING) as conn:
            cur=conn.cursor()
            cur.execute("""SELECT title,message,file_name FROM qr_codes WHERE code_id=%s""" % update)
            results = cur.fetchone()

        return read_html_file("update_page.html") % (results[0],results[1],update,results[0],results[1],results[2])

    @cherrypy.expose
    def update_code(self,new_title,new_message,new_file,update_id):

        with sqlite3.connect(DB_STRING) as conn:
            conn.execute("""UPDATE qr_codes SET title='%s',message='%s' WHERE code_id=%s""" % (new_title,new_message,update_id))

        if new_file.file is not None:
            self.save_file(new_file,str(update_id)+'.jpg','files')

        raise cherrypy.HTTPRedirect("/collection")

    ## VIEW PAGE & SUPPORTING FUNCTIONS

    @cherrypy.expose
    def view(self, file_name=0):

        connection = self.server_connect()
        cur = connection.cursor()
        cur.execute("""SELECT 1 FROM qr_codes WHERE file_name='%s'""" % (file_name))
        check1 = cur.fetchone()

        if check1 == None:
            return self.read_html_file("no_file.html")

        # add button to download code
        cur.execute("UPDATE qr_codes SET view_count = view_count+1 WHERE file_name='%s'" % file_name)
        connection.commit()
        connection.close()

        return read_html_file("view_page.html") % ('files/'+ file_name)


    ## GENERATE PAGE & SUPPORT FUNCTIONS FOR CREATING CODE

    @cherrypy.expose
    def generate(self):
        return read_html_file("generate_page.html")

    @cherrypy.expose
    def handle_form(self, title, message, file):

        id = self.add_code(title,message)

        url = cherrypy.request.headers['Host'] + '/view?file_name=' + str(id) + '.jpg'
        print(url)

        self.update_url(id,url)

        self.create_qr(id,url)

        self.save_file(file,str(id)+'.jpg','files')

        return read_html_file('handle_form.html')

    def add_code(self, title, message,url=''):
        connection = self.server_connect()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO qr_codes (title, message,qr_url,view_count) VALUES ('%s','%s','%s',0);""" % (title,message,url))

        id = cursor.lastrowid

        connection.commit()
        connection.close()

        return id

    def create_qr(self,id, url):
        qr = pyqrcode.create(url)

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(cur_dir, 'qr')
        qr.png(upload_path + '/' + str(id) + ".png", scale=8)

    def update_url(self,id,url):
        connection = self.server_connect()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE qr_codes 
            SET qr_url = '%s',
              file_name = '%s',
              qr_file = '%s'
            WHERE code_id = %s
            """ % (url,str(id)+'.jpg',str(id)+'.png',id))

        connection.commit()
        connection.close()

    def save_file(self,file,name,directory):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        upload_path = os.path.join(cur_dir,directory)

        upload_filename = name

        upload_file = os.path.normpath(
            os.path.join(upload_path, upload_filename))
        with open(upload_file, 'wb') as out:
            while True:
                data = file.file.read(8192)
                if not data:
                    break
                out.write(data)

    def server_connect(self):
        return sqlite3.connect('database.db')


@cherrypy.expose
class CodeTableGenerator(object):
    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        return ""

    def POST(self,action=False,code_id=None,new_title=None,new_message=None):
        if(action):
            delete_file('files', str(code_id) + '.jpg')
            delete_file('qr', str(code_id) + '.png')

            with sqlite3.connect(DB_STRING) as c:
                c.execute("DELETE FROM qr_codes WHERE code_id=?", [code_id])
            return ""
        else:
            id = cherrypy.session['update_id']

            with sqlite3.connect(DB_STRING) as c:
                c.execute("""
                  UPDATE qr_codes
                  SET title='%s',
                  message='%s'
                  WHERE code_id=%s
                  """ % (new_title,new_message,str(id)))

            return """{"id":"%s","title":"%s","message":"%s"}""" % (str(id),new_title,new_message)

    def PUT(self,update_id):
        cherrypy.session['update_id'] = update_id

    def DELETE(self):
        cherrypy.session['update_id'] = None

def create_table():
    with sqlite3.connect(DB_STRING) as con:
        table = pd.read_sql_query("SELECT * FROM qr_codes ORDER BY date_created DESC;", con)

        # code to generate the html for table rows
        table_html = ""

        for ind in table.index:
            table_html = table_html + ("""<tr id="%s">\n""" % str(table['code_id'][ind]))

            table_html = table_html + """
                        <td><div class="title">{}</div></td>
                        <td><div class="message">{}</div></td>
                        <td><div class="date">{}</div></td>
                        <td><div class="views">{}</div></td>
                        <td colspan="4"><a href="view?file_name={}"><button>View</button></a>
                        <a download href="{}"><button>Download</button></a>
                        <a href="/update?update={}"><button>Update</button></a>
                        <button class="delete-row" value="{}">Delete</button></td>
                        """.format(table['title'][ind], table['message'][ind], str(table['date_created'][ind]),
                                   str(table['view_count'][ind]),table['file_name'][ind], 'qr/' + str(table['qr_file'][ind]),
                                   str(table['code_id'][ind]),str(table['code_id'][ind]))

            table_html = table_html + "</tr>\n"
    return table_html

def delete_file(dir,file_name):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    relpath = dir + '/' + file_name
    path = os.path.join(cur_dir,relpath)
    os.unlink(path)

#READ HTML FILE
def read_html_file(filename):
    file = open("html/" + filename, 'r')
    return file.read()


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))

    config = {'/': {'tools.sessions.on': True,
                    'tools.response_headers.on':True},
              '/generator': {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                    'tools.response_headers.on': True,
                    'tools.response_headers.headers': [('Content-Type', 'text/plain')]},
              '/images': {'tools.staticdir.on': True,
                        'tools.staticdir.dir': os.path.join(current_dir, 'images')},
              '/css': {'tools.staticdir.on': True,
                       'tools.staticdir.dir': os.path.join(current_dir, 'css')},
              '/html': {'tools.staticdir.on': True,
                       'tools.staticdir.dir': os.path.join(current_dir, 'html')},
              '/qr': {'tools.staticdir.on': True,
                        'tools.staticdir.dir': os.path.join(current_dir, 'qr')},
              '/files': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(current_dir, 'files')}
              }
    #cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8010})

    webapp = Final_app()
    webapp.generator = CodeTableGenerator()

    cherrypy.quickstart(webapp, "/", config)
