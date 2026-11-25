import type { Config } from 'tailwindcss';
import sharedConfig from '@manutcar/config/tailwind.config';

const config: Config = {
  ...sharedConfig,
  content: [
    ...(Array.isArray(sharedConfig.content) ? sharedConfig.content : sharedConfig.content?.files ?? []),
    './src/**/*.{ts,tsx}',
  ],
};

export default config;
