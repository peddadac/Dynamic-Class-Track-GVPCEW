

pipeline {
    agent any

    environment {
        PYTHON = 'C:\\Users\\narad\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Source code fetched from GitHub.'
            }
        }

        stage('Verify Project') {
            steps {
                bat '"%PYTHON%" --version'
                bat 'git --version'
                bat 'dir'
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
    }

    post {
        success {
            echo 'Dynamic Class Track pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check Console Output.'
        }
    }
}
