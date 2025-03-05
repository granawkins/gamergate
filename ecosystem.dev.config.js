module.exports = {
    apps: [
      {
          name: 'gamergate-backend',
          cwd: './backend',
          script: 'uvicorn routes:app --reload --host 0.0.0.0 --port 8001',
          env: {
            NODE_ENV: 'development',
          },
      },     
      {
        name: 'gamergate-frontend',
        cwd: './frontend',
        script: 'npm run dev',
        env: {
          NODE_ENV: 'development',
        },
      },
    ],
  };
  