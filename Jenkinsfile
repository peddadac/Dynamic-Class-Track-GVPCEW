
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        PYTHON = 'C:\\Users\\narad\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
        DOCKER_IMAGE = 'peddadac/dynamic-class-track'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo 'Latest GitHub source code checked out.'
            }
        }

        stage('Verify Tools') {
            steps {
                bat '"%PYTHON%" --version'
                bat 'git --version'
                bat 'docker version'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '"%PYTHON%" -m pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                bat '"%PYTHON%" -m pytest -v'
            }
        }

        stage('Build Docker Image') {
            steps {
                bat 'docker build --progress=plain -t %DOCKER_IMAGE%:%BUILD_NUMBER% -t %DOCKER_IMAGE%:latest .'
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dct-dockerhub-jenkins-2026',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    bat 'powershell -NoProfile -Command "$env:DOCKERHUB_TOKEN | docker login --username $env:DOCKERHUB_USER --password-stdin"'

                    bat 'docker push %DOCKER_IMAGE%:%BUILD_NUMBER%'
                    bat 'docker push %DOCKER_IMAGE%:latest'
                }
            }
        }
    }

    post {
        success {
            echo 'CI pipeline completed: tests passed and Docker images pushed!'
        }

        failure {
            echo 'Pipeline failed. Check the stage and Console Output.'
        }
    }
}



        
