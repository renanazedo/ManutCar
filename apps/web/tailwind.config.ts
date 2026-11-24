import type { Config } from 'tailwindcss';
import sharedConfig from '@manutcar/config/tailwind.config';

const config: Config = {
  ...sharedConfig,
  content: [
    ...(sharedConfig.content || []),
    './src/**/*.{ts,tsx}',
  ],
};

export default config;
