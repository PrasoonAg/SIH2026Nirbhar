/// <reference types="vite/client" />

// Allow CSS modules and plain CSS imports
declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}

// Allow JSON imports
declare module '*.json' {
  const value: unknown;
  export default value;
}
