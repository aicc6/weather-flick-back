pipeline {
  agent any

  environment {
    DOCKER_IMAGE = 'slseongjunlee/weather-flick-back'
    CONTAINER_NAME = 'weather-flick-back'
    MAPPING_PORT = '8000:80'
  }

  options {
    buildDiscarder(logRotator(numToKeepStr: '10'))
    timeout(time: 30, unit: 'MINUTES')
    timestamps()
  }

  stages {
    stage('Clone Repository') {
      steps {
        checkout scm
      }
      post {
        failure {
          echo 'Repository clone failed'
        }
      }
    }

    stage('Build Image') {
      steps {
        script {
          try {
            def app = docker.build("${DOCKER_IMAGE}:${BUILD_NUMBER}")
            env.DOCKER_BUILD_SUCCESS = 'true'
          } catch (Exception e) {
            env.DOCKER_BUILD_SUCCESS = 'false'
            error "Docker build failed: ${e.getMessage()}"
          }
        }
      }
      post {
        failure {
          echo 'Docker image build failed'
        }
      }
    }

    stage('Push Image') {
      when {
        environment name: 'DOCKER_BUILD_SUCCESS', value: 'true'
      }
      steps {
        script {
          try {
            docker.withRegistry("https://${DOCKER_REGISTRY}", "${DOCKER_CREDENTIALS}") {
              def app = docker.image("${DOCKER_IMAGE}:${BUILD_NUMBER}")
              app.push("${BUILD_NUMBER}")
              app.push("latest")
            }
          } catch (Exception e) {
            error "Docker push failed: ${e.getMessage()}"
          }
        }
      }
      post {
        success {
          echo "Successfully pushed ${DOCKER_IMAGE}:${BUILD_NUMBER} and ${DOCKER_IMAGE}:latest"
        }
        failure {
          echo 'Docker image push failed'
        }
      }
    }

    stage('Deploy') {
      steps {
        sshagent(['lxl']) {
          sh """
              ssh -o StrictHostKeyChecking=no sl@${env.DEPLOY_SERVER} -p ${env.DEPLOY_SERVER_PORT} '
                  # 새 이미지 다운로드
                  docker pull ${env.DOCKER_REGISTRY}/${env.DOCKER_IMAGE}:${env.BUILD_ID}

                  # 기존 컨테이너 중지 및 삭제
                  docker stop ${env.CONTAINER_NAME} || true
                  docker rm ${env.CONTAINER_NAME} || true

                  # 새 컨테이너 실행
                  docker run -d \\
                      --name ${env.CONTAINER_NAME} \\
                      -p ${env.MAPPING_PORT} \\
                      --restart unless-stopped \\
                      ${env.DOCKER_REGISTRY}/${env.DOCKER_IMAGE}:${env.BUILD_ID}

                  # 이전 이미지 정리 (선택사항)
                  docker image prune -f
              '
          """
        }
      }
    }
  }

  post {
    always {
      script {
        try {
          sh 'docker system prune -f'
        } catch (Exception e) {
          echo "Docker cleanup failed: ${e.getMessage()}"
        }
      }
    }
    success {
      echo 'Pipeline completed successfully!'
    }
    failure {
      echo 'Pipeline failed!'
    }
    cleanup {
      deleteDir()
    }
  }
}
