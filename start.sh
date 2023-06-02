project_pid=`ps aux | grep "app.py" | grep -v grep | awk 'END{print $2}'`
if [  $project_pid > 0 ];then
echo "项目已经启动，开始关闭项目，项目pid为: $project_pid "
echo "--------------------"
kill -9 `ps aux | grep "app.py" | grep -v grep | awk 'END{print $2}'`
echo '项目关闭成功，开始重启项目 '
echo "--------------------"
else
echo "项目未启动，直接启动"
echo "--------------------"
fi
nohup python3 /home/data-visualization/app.py
check_pid=`ps aux | grep "app.py" | grep -v grep | awk 'END{print $2}'`
  if [ $check_pid  > 0 ];then
        echo "项目启动成功： pid = : $check_pid  "
  else
        echo "项目启动失败"
        exit 1
  fi