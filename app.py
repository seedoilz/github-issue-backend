import os.path

from flask import Flask, request, jsonify
from markupsafe import Markup
import requests
import datetime
import pymysql
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Bar

app = Flask(__name__, static_folder="templates")


def bar_base() -> Bar:
    c = (
        Bar()
        .add_xaxis(["衬衫", "羊毛衫", "雪纺衫", "裤子", "高跟鞋", "袜子"])
        .add_yaxis("商家A", [5, 20, 36, 10, 75, 90])
        .add_yaxis("商家B", [15, 25, 16, 55, 48, 8])
        .set_global_opts(title_opts=opts.TitleOpts(title="Bar-基本示例", subtitle="我是副标题"))
    )
    return c


@app.route("/")
def index():
    c = bar_base()
    return Markup(c.render_embed())


@app.route("/process", methods=['POST'])
def process():
    try:
        project = request.form['project']
        version = request.form['version']
        web_address = request.form['web-address']
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "获取表单数据出错",
            "detail": str(e)
        }), 400

    try:
        folder_path = spider(project, version, web_address)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "爬虫处理出错",
            "detail": str(e)
        }), 400

    try:
        remove_citation(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "删除引用出错",
            "detail": str(e)
        }), 400

    try:
        format_files(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "格式化出错",
            "detail": str(e)
        }), 400

    try:
        analyze(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "分析出错",
            "detail": str(e)
        }), 400

    try:
        pass_to_database(folder_path, project)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "存储到数据库出错",
            "detail": str(e)
        }), 400

    return jsonify({
        "status": "success",
        "message": "处理成功"
    }), 200


def pass_to_database(folder_path, project):
    db = pymysql.connect(host='localhost',
                         user='root',
                         password='Czy026110',
                         database='homework')
    cursor = db.cursor()
    cursor.execute(f"SHOW TABLES LIKE '{'project_' + project}'")
    table_exists = cursor.fetchone() is not None
    if not table_exists:
        sql = "CREATE TABLE project_" + project + " (issue_number INT NOT NULL,internal_issue_number INT NOT NULL," \
                                                  "username VARCHAR(255) NOT NULL," \
                                                  "created_at DATETIME NOT NULL," \
                                                  "ended_at DATETIME," \
                                                  "is_pull_request TINYINT(1) NOT NULL," \
                                                  "labels VARCHAR(255)," \
                                                  "project_name VARCHAR(255) NOT NULL," \
                                                  "version_number VARCHAR(255)," \
                                                  "content TEXT," \
                                                  "positive_score INT," \
                                                  "negative_score INT," \
                                                  "PRIMARY KEY (issue_number,internal_issue_number))"
        cursor.execute(sql)
    sql = "INSERT INTO project_" + project + " (issue_number, internal_issue_number, " \
                                             "username, created_at, ended_at, " \
                                             "is_pull_request, labels, " \
                                             "project_name, version_number, " \
                                             "content, positive_score, negative_score) " \
                                             "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

    for filename in os.listdir(folder_path):
        if filename == '.DS_Store':
            continue
        if filename.startswith('FORMAT'):
            continue
        file_path = os.path.join(folder_path, filename)
        project_name = ''
        version_number = ''
        issue_number = ''
        created_at = ''
        ended_at = ''
        is_pull_request = -1
        labels = ''
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                lines = file.readlines()
                project_name = lines[1].replace('\r', '').replace('\n', '')
                version_number = lines[2].replace('\r', '').replace('\n', '')
                issue_number = lines[3].replace('\r', '').replace('\n', '')
                usernames = [lines[4].replace('\r', '').replace('\n', '')]
                append_name = False
                for index, line in enumerate(lines):
                    if line == 'COMMENT_INFO\n':
                        append_name = True
                        continue
                    if append_name:
                        usernames.append(line.replace('\r', '').replace('\n', ''))
                        append_name = False
                created_at = lines[5].replace('\r', '').replace('\n', '')
                cdt = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                cdate = cdt.date()
                ctime = cdt.time()
                created_at = str(cdate) + ' ' + str(ctime)
                ended_at = lines[6].replace('\r', '').replace('\n', '')
                if ended_at != 'None':
                    edt = datetime.datetime.strptime(ended_at, "%Y-%m-%dT%H:%M:%SZ")
                    edate = edt.date()
                    etime = edt.time()
                    ended_at = str(edate) + ' ' + str(etime)
                if lines[7].replace('\r', '').replace('\n', '') == 'not_pull_request':
                    is_pull_request = 0
                else:
                    is_pull_request = 1
                labels = lines[8].replace('\r', '').replace('\n', '')
                file.close()

        result_filename = 'FORMAT' + filename.replace('.txt', '') + '0_out.txt'
        result_file_path = os.path.join(folder_path, result_filename)
        if os.path.isfile(result_file_path):
            df = pd.read_csv(result_file_path, sep='\t', header=None, skiprows=[0])
            df.columns = ['Positive', 'Negative', 'Text']
            for index, row in df.iterrows():
                positive_score = row['Positive']
                negative_score = row['Negative']
                content = row['Text']
                internal_issue_number = index
                try:
                    cursor.execute(sql, (
                        issue_number, internal_issue_number, usernames[index], created_at, ended_at, is_pull_request,
                        labels, project_name, version_number, content, positive_score, negative_score))
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise e
    db.close()


def analyze(folder_path):
    for filename in os.listdir(folder_path):
        if not filename.startswith("FORMAT"):
            continue
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.system('java -jar SentiStrength.jar input ' + file_path)


def remove_citation(folder_path):
    for filename in os.listdir(folder_path):
        if filename == '.DS_Store':
            continue
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r+') as file:
                lines = file.readlines()
                pred_line = 'BEGIN_ISSUE'
                del_lines = []
                for index, line in enumerate(lines):
                    if line.startswith('>') and pred_line == 'BEGIN_COMMENT\n':
                        del_lines.append(index)
                    pred_line = line
                for del_index in del_lines:
                    del lines[del_index]
                file.seek(0)
                file.truncate(0)
                file.writelines(lines)
                file.close()


def format_files(folder_path):
    for filename in os.listdir(folder_path):
        if filename == '.DS_Store':
            continue
        file_path = os.path.join(folder_path, filename)
        if filename.startswith('FORMAT'):
            continue
        if os.path.isfile(file_path):
            with open(file_path, 'r+') as file:
                lines = file.readlines()
                new_file_name = "FORMAT" + filename
                new_file_path = os.path.join(folder_path, new_file_name)
                new_line = ""
                skip = False
                with open(new_file_path, 'w') as new_file:
                    for index, line in enumerate(lines):
                        if index <= 9:
                            continue
                        if skip:
                            if line == 'BEGIN_COMMENT\n':
                                skip = False
                                continue
                            else:
                                continue
                        if line == 'COMMENT_INFO\n':
                            new_file.write(new_line)
                            new_file.write("\r\n")
                            new_line = ""
                            skip = True
                        elif index == len(lines) - 1:
                            new_line = new_line + line.replace("\n", " ").replace("\r", " ")
                            new_file.write(new_line)
                            new_file.write("\r\n")
                        else:
                            new_line = new_line + line.replace("\n", " ").replace("\r", " ")
                    new_file.close()
                file.close()


def spider(project, version, web_address):
    headers = {
        'Authorization': 'token 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',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {
        "labels": version,
        "state": "all"
    }
    api_url = web_address + '?'

    version = version.replace('/', ':')

    if not os.path.exists('./data'):
        os.mkdir('./data')
    if not os.path.exists('./data/' + project):
        os.mkdir('./data/' + project)
    if not os.path.exists('./data/' + project + '/' + version):
        os.mkdir('./data/' + project + '/' + version)
    file_saved_path = './data/' + project + '/' + version

    page = 1
    while True:
        response = requests.get(api_url + f'&per_page=100&page={page}', params=params, headers=headers)
        issues = response.json()
        if not issues:
            break
        for issue in issues:
            if issue is None:
                continue
            if issue == 'message' or issue == 'documentation_url':
                continue
            if issue['body'] is None:
                continue
            index = issue['number']
            index = str(index)
            labels_info = issue['labels']
            labels = []
            for label_info in labels_info:
                labels.append(label_info['name'])
            created_at = issue['created_at']
            closed_at = issue['closed_at']
            if 'pull_request' in issue:
                pull_request = True
            else:
                pull_request = False
            user_info = issue['user']
            user = user_info['login']
            with open(file_saved_path + '/' + project + '_' + index + '.txt', 'w') as f:
                f.write('ISSUE_INFO\r\n')
                f.write(project)
                f.write('\r\n')
                f.write(version)
                f.write('\r\n')
                f.write(index)
                f.write('\r\n')
                f.write(str(user))
                f.write('\r\n')
                f.write(str(created_at))
                f.write('\r\n')
                f.write(str(closed_at))
                f.write('\r\n')
                if (pull_request):
                    f.write('pull_request')
                    f.write('\r\n')
                else:
                    f.write('not_pull_request')
                    f.write('\r\n')
                for label in labels:
                    f.write(label + ',')
                f.write('\r\n')
                f.write('BEGIN_ISSUE\r\n')
                f.write(issue['body'])
                f.write('\r\n')
                comments_url = issue['comments_url']
                response = requests.get(comments_url, headers=headers)
                comments = response.json()
                for comment in comments:
                    if comment is None:
                        continue
                    if comment == 'message' or comment == 'documentation_url':
                        continue
                    f.write('COMMENT_INFO')
                    f.write('\r\n')
                    f.write(comment['user']['login'])
                    f.write('\r\n')
                    f.write(str(created_at))
                    f.write('\r\n')
                    f.write('BEGIN_COMMENT\r\n')
                    f.write(comment['body'])
                    f.write('\r\n')
                f.close()
        page = page + 1
    return file_saved_path


if __name__ == "__main__":
    app.run()
