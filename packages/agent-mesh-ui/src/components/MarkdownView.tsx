import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

/**
 * Renders agent markdown output. Designed to be extended with rich code-block
 * renderers (e.g. ```spl, ```splunk-chart) once skills land. For v1, all code
 * blocks fall through to the default plain renderer.
 *
 * To add a custom renderer later, pass:
 *   <MarkdownView content={md} codeBlockRenderers={{ 'splunk-chart': ChartBlock }} />
 *
 * A renderer receives { language, value } and returns a React element.
 */

export type CodeBlockRenderer = (props: { language: string; value: string }) => React.ReactElement | null;

export interface MarkdownViewProps {
    content: string;
    codeBlockRenderers?: Record<string, CodeBlockRenderer>;
}

const MarkdownContainer = styled.div`
    color: ${variables.contentColorDefault};
    line-height: 1.55;

    h1, h2, h3, h4 {
        margin-top: ${variables.spacingMedium};
        margin-bottom: ${variables.spacingSmall};
        color: ${variables.contentColorActive};
    }

    h1 { font-size: ${variables.fontSizeXXLarge}; }
    h2 { font-size: ${variables.fontSizeXLarge}; }
    h3 { font-size: ${variables.fontSizeLarge}; }

    p, ul, ol, blockquote {
        margin-top: ${variables.spacingSmall};
        margin-bottom: ${variables.spacingSmall};
    }

    ul, ol { padding-left: 1.4em; }
    li { margin-bottom: 4px; }

    blockquote {
        border-left: 3px solid ${variables.borderColorStrong};
        margin-left: 0;
        padding-left: ${variables.spacingMedium};
        color: ${variables.contentColorMuted};
    }

    a {
        color: ${variables.interactiveColorPrimary};
        text-decoration: none;
    }
    a:hover { text-decoration: underline; }

    code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.92em;
        padding: 2px 4px;
        background: ${variables.backgroundColorSidebar};
        border-radius: 3px;
    }

    pre {
        background: ${variables.backgroundColorSidebar};
        border: 1px solid ${variables.borderColor};
        border-radius: 4px;
        padding: ${variables.spacingSmall} ${variables.spacingMedium};
        overflow-x: auto;
    }

    pre code {
        background: transparent;
        padding: 0;
    }

    table {
        border-collapse: collapse;
        margin: ${variables.spacingSmall} 0;
        width: 100%;
    }
    th, td {
        border: 1px solid ${variables.borderColor};
        padding: 6px 10px;
        text-align: left;
        vertical-align: top;
    }
    th {
        background: ${variables.backgroundColorSidebar};
        font-weight: ${variables.fontWeightSemiBold};
    }

    hr {
        border: none;
        border-top: 1px solid ${variables.borderColor};
        margin: ${variables.spacingMedium} 0;
    }
`;

const MarkdownView: React.FC<MarkdownViewProps> = ({ content, codeBlockRenderers }) => {
    const components: any = {};
    if (codeBlockRenderers && Object.keys(codeBlockRenderers).length > 0) {
        components.code = ({ inline, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';
            const renderer = !inline && language ? codeBlockRenderers[language] : undefined;
            if (renderer) {
                const value = String(children).replace(/\n$/, '');
                return renderer({ language, value });
            }
            return (
                <code className={className} {...props}>
                    {children}
                </code>
            );
        };
    }

    return (
        <MarkdownContainer>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeSanitize]}
                components={components}
            >
                {content}
            </ReactMarkdown>
        </MarkdownContainer>
    );
};

export default MarkdownView;
