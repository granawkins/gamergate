module.exports = {
    apps: [
      {
          name: 'gamergate-backend',
          cwd: './backend',
          script: 'uvicorn routes:app --host 0.0.0.0 --port 8001',
          env: {
            NODE_ENV: 'production',
          },
      }
    ],
  };
  