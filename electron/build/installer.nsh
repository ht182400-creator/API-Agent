; NSIS 安装脚本 - 自定义安装步骤

; 安装 Docker Desktop (如果未安装)
!macro customInstall
  ; 检查 Docker 是否已安装
  ReadRegStr $0 HKLM "SOFTWARE\Docker Inc.\Docker\1.0" "InstallPath"
  
  ${If} $0 == ""
    ; Docker 未安装，询问用户是否安装
    MessageBox MB_YESNO|MB_ICONQUESTION "检测到 Docker Desktop 未安装，是否现在安装？$\r$\n$\r$\nDocker 是运行 API Platform 所必需的。" IDYES install_docker IDNO skip_docker
    
    install_docker:
      DetailPrint "正在安装 Docker Desktop..."
      File /oname=$PLUGINSDIR\DockerDesktopInstaller.exe "..\dependencies\DockerDesktopInstaller.exe"
      ExecWait '"$PLUGINSDIR\DockerDesktopInstaller.exe" install --quiet --accept-license'
      Goto done_install
      
    skip_docker:
      MessageBox MB_OK|MB_ICONEXCLAMATION "警告：Docker Desktop 未安装。$\r$\n$\r$\n请手动安装 Docker Desktop 后再运行 API Platform。"
      Goto done_install
      
    done_install:
  ${EndIf}
  
  ; 复制 Docker 配置文件
  DetailPrint "正在配置 Docker..."
  SetOutPath "$INSTDIR\docker"
  File /r "..\docker\*.*"
  
  ; 创建启动脚本
  FileOpen $0 "$INSTDIR\start.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd %~dp0$\r$\n"
  FileWrite $0 "cd docker$\r$\n"
  FileWrite $0 "docker-compose up -d$\r$\n"
  FileWrite $0 "start http://localhost$\r$\n"
  FileClose $0
  
  ; 创建停止脚本
  FileOpen $0 "$INSTDIR\stop.bat" w
  FileWrite $0 "@echo off$\r$\n"
  FileWrite $0 "cd %~dp0$\r$\n"
  FileWrite $0 "cd docker$\r$\n"
  FileWrite $0 "docker-compose down$\r$\n"
  FileClose $0
!macroend

; 卸载时清理
!macro customUnInstall
  ; 停止 Docker 服务
  ExecWait '"$INSTDIR\stop.bat"'
  
  ; 删除数据卷 (询问用户)
  MessageBox MB_YESNO|MB_ICONQUESTION "是否删除所有数据 (数据库、缓存等)？$\r$\n$\r$\n选择"是"将永久删除所有数据！" IDYES delete_data IDNO skip_delete
    
    delete_data:
      ExecWait 'docker-compose -f "$INSTDIR\docker\docker-compose.yml" down -v'
      Goto done_delete
      
    skip_delete:
      ExecWait 'docker-compose -f "$INSTDIR\docker\docker-compose.yml" down'
      
    done_delete:
  
  ; 删除安装目录
  RMDir /r "$INSTDIR"
!macroend
