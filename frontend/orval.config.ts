import { defineConfig } from 'orval'

const input = process.env.ORVAL_INPUT ?? './openapi/company-system.openapi.json'
const output = process.env.ORVAL_OUTPUT ?? './src/api/generated/company-system.ts'

export default defineConfig({
  companySystem: {
    input: {
      target: input,
    },
    output: {
      baseUrl: {
        runtime: "import.meta.env.VITE_API_ORIGIN || ''",
      },
      client: 'fetch',
      fileExtension: '.ts',
      mode: 'single',
      override: {
        fetch: {
          includeHttpResponseReturnType: true,
        },
      },
      target: output,
    },
  },
})
