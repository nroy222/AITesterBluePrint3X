# Playwright API Automation Framework

## Folder structure

API RestAssured Playwright/
├─ fixtures/
│  └─ users/
│     └─ create-user.json
├─ src/
│  ├─ api/
│  │  ├─ baseApiClient.ts
│  │  └─ services/
│  │     └─ usersApi.ts
│  ├─ config/
│  │  └─ env.ts
│  └─ types/
│     └─ api.ts
├─ tests/
│  └─ api/
│     └─ users.spec.ts
├─ .env.example
├─ package.json
├─ playwright.config.ts
└─ tsconfig.json

## VS Code terminal commands

1. cd "c:\Users\dhana\OneDrive\Desktop\API RestAssured Playwright"
2. npm install
3. npx playwright install chromium
4. copy .env.example .env
5. npx playwright test tests/api/users.spec.ts --reporter=html
6. npx playwright show-report

This framework uses JSONPlaceholder for a stable CRUD example without API-key authentication.
