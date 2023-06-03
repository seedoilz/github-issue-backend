import os.path
import re
from flask import Flask, request, jsonify
from flask_cors import cross_origin
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import requests
import datetime
import pymysql
import pandas as pd
import nltk

app = Flask(__name__, static_folder="templates")


# nltk.download('averaged_perceptron_tagger')
# nltk.download('nps_chat')
# nltk.download('stopwords')

@app.route("/weight", methods=['POST'])
@cross_origin()
def word_weight():
    project = request.form['project']
    version = request.form['version']
    # db = pymysql.connect(host='localhost',
    #                      user='root',
    #                      password='Czy026110',
    #                      database='homework')
    db = pymysql.connect(host='124.70.198.102',
                         user='root',
                         password='HaRdEsTnju@123',
                         database='sentistrength')
    cursor = db.cursor()
    project_name = project + '_' + version
    if version == '':
        project_name = project

    exist_sql = "SELECT weight_id from collection_weight WHERE collection_id = (SELECT id from collection WHERE name = %s)"
    cursor.execute(exist_sql, (project_name,))
    result = cursor.fetchall()
    if len(result) == 0:
        cursor.execute('SELECT id from collection WHERE name = %s', (project_name))
        collection_id = cursor.fetchone()[0]
        select_id_sql = "SELECT data_id from collection_data WHERE collection_id = (SELECT id from collection WHERE name = %s)"
        cursor.execute(select_id_sql, (project_name,))
        ids = cursor.fetchall()
        id_list = [row[0] for row in ids]
        select_content_sql = "SELECT content FROM data WHERE id IN ({})".format(','.join(['%s'] * len(id_list)))
        cursor.execute(select_content_sql, id_list)
        content_list = cursor.fetchall()
        content_results = [row[0] for row in content_list]

        combined_content = [' '.join(content_results)]
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(combined_content)
        feature_names = vectorizer.get_feature_names_out()

        tfidf_array = tfidf.toarray()
        top_n_idx = np.argsort(tfidf_array[0])[-500:]
        top_n_values = [tfidf_array[0][i] for i in top_n_idx]
        top_n_words = [feature_names[i] for i in top_n_idx]

        word_dict = dict(zip(top_n_words, top_n_values))

        nltk_data = nltk.corpus.nps_chat.tagged_words()
        nouns = [word.lower() for (word, tag) in nltk_data if tag.startswith('N')]
        sw_nltk = stopwords.words('english')
        res_list = []
        for key in list(word_dict.keys()):
            if key not in nouns or key in sw_nltk or key == 'comment' or key == 'comments' or key.isnumeric():
                # 删除键及其对应的值
                del word_dict[key]
            else:
                word_dict[key] = int(word_dict[key] * 10000 // 1)
                temp = {'name': key, 'value': word_dict[key]}
                res_list.append(temp)

        weight_insert_sql = "INSERT IGNORE INTO weight (collection_id, name, weight) VALUES (%s, %s, %s)"
        collection_weight_insert_sql = "INSERT IGNORE INTO collection_weight (collection_id, weight_id) VALUES (%s, %s)"
        weight_select_sql = "SELECT id FROM weight WHERE collection_id = %s"
        for res in res_list:
            cursor.execute(weight_insert_sql, (collection_id, res['name'], res['value']))
        db.commit()

        cursor.execute(weight_select_sql, collection_id)
        weight_ids_list = cursor.fetchall()
        for weight_id in list(weight_ids_list):
            cursor.execute(collection_weight_insert_sql, (collection_id, weight_id))
        db.commit()
        return jsonify({
            "status": "success",
            "message": "success",
            "data": res_list
        })
    else:
        weight_id_list = [row[0] for row in result]
        select_weight_sql = "SELECT name, weight FROM weight WHERE id IN ({})".format(
            ','.join(['%s'] * len(weight_id_list)))
        cursor.execute(select_weight_sql, weight_id_list)
        ret_list = cursor.fetchall()
        res_list = []
        for item in ret_list:
            temp = {'name': item[0], 'value': item[1]}
            res_list.append(temp)
        print("through database")
        return jsonify({
            "status": "success",
            "message": "success",
            "data": res_list
        })


@app.route("/process", methods=['POST'])
@cross_origin()
def process():
    try:
        project = request.form['project']
        version = request.form['version']
        web_address = request.form['web-address']
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "form data error",
            "detail": str(e)
        }), 400
    folder_path = './data/' + project + '/' + version
    try:
        folder_path = spider(project, version, web_address)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "spider error",
            "detail": str(e)
        }), 400

    try:
        remove_citation(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "remove citation error",
            "detail": str(e)
        }), 400

    try:
        format_files(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "format error",
            "detail": str(e)
        }), 400

    try:
        analyze(folder_path)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "analyze error",
            "detail": str(e)
        }), 400

    try:
        pass_to_database(folder_path, project, version)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "database error",
            "detail": str(e)
        }), 400

    return jsonify({
        "status": "success",
        "message": "dealing success"
    }), 200


def pass_to_database(folder_path, project, version):
    # 连接数据库
    # db = pymysql.connect(host='localhost',
    #                      user='root',
    #                      password='Czy026110',
    #                      database='homework')
    db = pymysql.connect(host='124.70.198.102',
                         user='root',
                         password='HaRdEsTnju@123',
                         database='sentistrength')
    cursor = db.cursor()
    # cursor.execute(f"SHOW TABLES LIKE '{'project_' + project}'")
    # table_exists = cursor.fetchone() is not None
    # if not table_exists:
    #     sql = "CREATE TABLE project_" + project + " (issue_number INT NOT NULL,internal_issue_number INT NOT NULL," \
    #                                               "username VARCHAR(255) NOT NULL," \
    #                                               "created_at DATETIME NOT NULL," \
    #                                               "ended_at DATETIME," \
    #                                               "is_pull_request TINYINT(1) NOT NULL," \
    #                                               "labels VARCHAR(255)," \
    #                                               "project_name VARCHAR(255) NOT NULL," \
    #                                               "version_number VARCHAR(255)," \
    #                                               "content TEXT," \
    #                                               "positive_score INT," \
    #                                               "negative_score INT," \
    #                                               "PRIMARY KEY (issue_number,internal_issue_number))"
    #     cursor.execute(sql)
    sql = "INSERT IGNORE INTO data" + " (issue_number, internal_issue_number, " \
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
            with open(file_path, 'r', encoding='utf-8') as file:
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
                else:
                    ended_at = None
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
                content = remove_emoji(content)
                internal_issue_number = index
                # print(content)
                try:
                    cursor.execute(sql, (
                        issue_number, internal_issue_number, usernames[index], created_at, ended_at, is_pull_request,
                        labels, project_name, version_number, content, positive_score, negative_score))
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise e

    # collection table
    collection_name = project + '_' + version
    collection_sql = "INSERT IGNORE INTO collection " + "(name) VALUE (%s)"
    cursor.execute(collection_sql, collection_name)
    db.commit()

    # data_id sql
    if '\'' in collection_name:
        collection_name = collection_name.replace('\'', '\\\'')
    if '\'' in version:
        version = version_number.replace('\'', '\\\'')
    collection_id_sql = "SELECT id FROM collection WHERE name = \'" + collection_name + "\'"
    cursor.execute(collection_id_sql)
    collection_id = cursor.fetchone()
    data_id_sql = "SELECT id FROM data WHERE version_number = \'" + version + "\'" + " and project_name = \'" + project + "\'"
    cursor.execute(data_id_sql)
    data_id_list = cursor.fetchall()
    collection_data_sql = "INSERT IGNORE INTO collection_data " + "(collection_id, data_id) VALUES " + "(%s, %s)"
    for data_id in list(data_id_list):
        cursor.execute(collection_data_sql, (collection_id, data_id))
    db.commit()
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
        print(filename)
        if filename == '.DS_Store':
            continue
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r+', encoding='utf-8') as file:
                lines = file.readlines()
                pred_line = 'BEGIN_ISSUE'
                del_lines = []
                for index, line in enumerate(lines):
                    if line.startswith('> ') and pred_line == 'BEGIN_COMMENT\n':
                        del_lines.append(index)
                    pred_line = line
                for del_index in sorted(del_lines, reverse=True):
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
            with open(file_path, 'r+', encoding='utf-8') as file:
                lines = file.readlines()
                new_file_name = "FORMAT" + filename
                new_file_path = os.path.join(folder_path, new_file_name)
                new_line = ""
                skip = False
                with open(new_file_path, 'w', encoding='utf-8') as new_file:
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
            with open(file_saved_path + '/' + project + '_' + index + '.txt', 'w', encoding='utf-8') as f:
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


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
