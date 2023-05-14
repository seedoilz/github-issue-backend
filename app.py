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


@app.route("/spider", methods=['POST'])
def spider():
    project = request.form['project']
    version = request.form['version']
    web_address = request.form['web-address']
    headers = {
        'Authorization': 'token YOUR_TOKEN',
        'Accept': 'application/vnd.github.v3+json'
    }
    params = {
        "labels": version,
        "state": "all"
    }
    api_url = web_address + '?'
    if start_spider(headers, params, api_url, project):
        return "success"
    else:
        return "failure"


def start_spider(headers, params, api_url, project):
    page = 1
    while True:
        response = requests.get(api_url + f'&per_page=100&page={page}', params=params, headers=headers)
        issues = response.json()
        print(issues)
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
            with open('./data/superset_' + index + '.txt', 'w') as f:
                f.write('ISSUE_INFO\r\n')
                f.write(project)
                f.write('\r\n')
                f.write(params['version'])
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


if __name__ == "__main__":
    app.run()
