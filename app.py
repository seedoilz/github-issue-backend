import os.path

from flask import Flask, request
from markupsafe import Markup
import requests

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
    project = request.form['project']
    version = request.form['version']
    web_address = request.form['web-address']
    folder_path = spider(project, version, web_address)
    remove_citation(folder_path)
    format(folder_path)
    analyze(folder_path)
    return "success"


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
                pred_line = 'ANOTHER_TEXT_BEGIN'
                del_lines = []
                for index, line in enumerate(lines):
                    if line.startswith('>') and pred_line == 'ANOTHER_TEXT_BEGIN\n':
                        del_lines.append(index)
                    pred_line = line
                for del_index in del_lines:
                    del lines[del_index]
                file.seek(0)
                file.truncate(0)
                file.writelines(lines)
                file.close()

def format(folder_path):
    for filename in os.listdir(folder_path):
        if filename == '.DS_Store':
            continue
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r+') as file:
                lines = file.readlines()
                new_file_name = "FORMAT" + filename
                new_file_path = os.path.join(folder_path, new_file_name)
                new_line = ""
                with open(new_file_path, 'w') as new_file:
                    for index, line in enumerate(lines):
                        if index <= 9:
                            continue
                        if line == 'ANOTHER_TEXT_BEGIN\n':
                            new_file.write(new_line)
                            new_file.write("\r\n")
                            new_line = ""
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
                f.write(params['labels'])
                f.write('\r\n')
                f.write(index)
                f.write('\r\n')
                f.write(str(user))
                f.write('\r\n')
                f.write(str(created_at))
                f.write('\r\n')
                f.write(str(closed_at))
                f.write('\r\n')
                if pull_request:
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
                f.write('\r\nANOTHER_TEXT_BEGIN\r\n')
                comments_url = issue['comments_url']
                response = requests.get(comments_url, headers=headers)
                comments = response.json()
                for comment in comments:
                    if comment is None:
                        continue
                    if comment == 'message' or comment == 'documentation_url':
                        continue
                    f.write(comment['body'])
                    f.write('\r\nANOTHER_TEXT_BEGIN\r\n')
                f.close()
        page = page + 1
    return file_saved_path


if __name__ == "__main__":
    app.run()
