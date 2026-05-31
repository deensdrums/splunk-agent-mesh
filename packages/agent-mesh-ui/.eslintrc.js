module.exports = {
    parser: '@typescript-eslint/parser',
    plugins: ['@typescript-eslint'],
    extends: ['@splunk/eslint-config/base', '@splunk/eslint-config/browser-prettier'],
    rules: {
        'react/jsx-filename-extension': ['error', { extensions: ['.tsx', '.jsx'] }],
        // without this rule, unit test files will fail for importing devDependency packages
        'import/no-extraneous-dependencies': [
            'error',
            {
                devDependencies: ['src/**/tests/*.unit*'],
            },
        ],
        // TypeScript already resolves identifiers (DOM lib types like RequestInit,
        // module `require`, etc.), so the core no-undef rule produces false positives.
        // This is the typescript-eslint recommended configuration.
        'no-undef': 'off',
        'no-unused-vars': 'off',
        '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
        // Injected at runtime by the host page; the dunder name is intentional.
        'no-underscore-dangle': ['error', { allow: ['__AGENT_MESH_API_URL__'] }],
    },
    overrides: [
        {
            files: ['src/**/tests/*.unit*'],
            env: {
                jest: true,
            },
        },
        {
            // Legacy components are not on the active investigation path and use
            // stable, static arrays where an index key is acceptable.
            files: ['src/components/legacy/**'],
            rules: {
                'react/no-array-index-key': 'off',
            },
        },
    ],
};
