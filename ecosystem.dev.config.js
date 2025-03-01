module.exports = {
    apps: [
      {
          name: 'gamergate-backend',
          cwd: './backend',
          script: 'uvicorn main:app --reload',
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
  