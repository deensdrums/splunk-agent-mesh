import React from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import Message from '@splunk/react-ui/Message';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import Column from '@splunk/visualizations/Column';
import Line from '@splunk/visualizations/Line';
import Pie from '@splunk/visualizations/Pie';
import { Artifact, SearchArtifact } from '../types';

interface Props {
    artifact: Artifact;
    embedded?: boolean;
}

const Card = styled.div`
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    background: ${variables.backgroundColorNavigation};
    margin: ${variables.spacingMedium} 0;
    overflow: hidden;
`;

const Header = styled.div`
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    border-bottom: 1px solid ${variables.borderColor};
    display: flex;
    justify-content: space-between;
    gap: ${variables.spacingMedium};
`;

const Title = styled.div`
    font-weight: ${variables.fontWeightSemiBold};
`;

const Meta = styled.div`
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
`;

const Body = styled.div`
    padding: ${variables.spacingMedium};
`;

const EmbeddedArtifact = styled.div`
    margin-top: ${variables.spacingMedium};
    padding-top: ${variables.spacingSmall};
    border-top: 1px solid ${variables.borderColor};
`;

const EmbeddedMeta = styled.div`
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: ${variables.spacingSmall} ${variables.spacingMedium};
    margin-bottom: ${variables.spacingSmall};
`;

const SplBlock = styled.pre`
    background: ${variables.backgroundColorSidebar};
    border: 1px solid ${variables.borderColor};
    border-radius: 4px;
    overflow-x: auto;
    padding: ${variables.spacingSmall};
`;

const DataTable = styled.table`
    border-collapse: collapse;
    width: 100%;
    margin-top: ${variables.spacingSmall};

    th, td {
        border: 1px solid ${variables.borderColor};
        padding: 6px 8px;
        text-align: left;
        vertical-align: top;
    }

    th {
        background: ${variables.backgroundColorSidebar};
    }
`;

const Bars = styled.div`
    display: flex;
    align-items: end;
    gap: 8px;
    height: 160px;
    border-left: 1px solid ${variables.borderColor};
    border-bottom: 1px solid ${variables.borderColor};
    padding: ${variables.spacingSmall};
    overflow-x: auto;
`;

const Bar = styled.div<{ height: number }>`
    background: ${variables.interactiveColorPrimary};
    min-width: 24px;
    height: ${({ height }) => `${Math.max(height, 2)}%`};
`;

const SingleValue = styled.div`
    font-size: 32px;
    font-weight: ${variables.fontWeightBold};
    margin: ${variables.spacingMedium} 0;
`;

const SearchState = styled.div<{ $status: SearchArtifact['status'] }>`
    display: flex;
    align-items: center;
    gap: ${variables.spacingSmall};
    padding: ${variables.spacingSmall};
    margin-bottom: ${variables.spacingSmall};
    border-left: 3px solid ${({ $status }) =>
        $status === 'done' ? variables.statusColorLow : variables.statusColorInfo};
    background: ${variables.backgroundColorSidebar};
    color: ${variables.contentColorDefault};
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
`;

const RowsTable: React.FC<{ fields: string[]; rows: Record<string, unknown>[] }> = ({ fields, rows }) => (
    <DataTable>
        <thead>
            <tr>
                {fields.map((field) => (
                    <th key={field}>{field}</th>
                ))}
            </tr>
        </thead>
        <tbody>
            {rows.map((row) => (
                <tr key={JSON.stringify(row)}>
                    {fields.map((field) => (
                        <td key={field}>{String(row[field] ?? '')}</td>
                    ))}
                </tr>
            ))}
        </tbody>
    </DataTable>
);

function inferFields(rows: Record<string, unknown>[]): string[] {
    const fields: string[] = [];
    rows.forEach((row) => {
        Object.keys(row).forEach((field) => {
            if (!fields.includes(field)) {
                fields.push(field);
            }
        });
    });
    return fields;
}

function toNumber(value: unknown): number {
    if (typeof value === 'number') {
        return value;
    }
    if (typeof value === 'string') {
        return Number(value.replace(/,/g, ''));
    }
    return Number.NaN;
}

function firstNumericField(fields: string[], rows: Record<string, unknown>[]): string | undefined {
    return fields.find((field) => field !== '_time' && rows.some((row) => !Number.isNaN(toNumber(row[field]))));
}

function toColumnMajor(
    fields: string[],
    rows: Record<string, unknown>[]
): { fields: { name: string }[]; columns: string[][] } {
    return {
        fields: fields.map((name) => ({ name })),
        columns: fields.map((fieldName) =>
            rows.map((row) => String(row[fieldName] ?? ''))
        ),
    };
}

function renderViz(artifact: SearchArtifact, fields: string[], rows: Record<string, unknown>[]) {
    if (rows.length === 0) {
        return <Message type="info">No rows returned.</Message>;
    }
    if (artifact.visualization.kind === 'single') {
        const metric = firstNumericField(fields, rows);
        return <SingleValue>{metric ? String(rows[0][metric]) : String(Object.values(rows[0])[0])}</SingleValue>;
    }
    if (artifact.visualization.kind === 'timechart') {
        const columnData = toColumnMajor(fields, rows);
        return (
            <div style={{ width: '100%', overflowX: 'auto' }}>
                <Column
                    width={700}
                    height={250}
                    dataSources={{
                        primary: {
                            data: columnData,
                            meta: {},
                            requestParams: {},
                        },
                    }}
                />
            </div>
        );
    }
    if (artifact.visualization.kind === 'line') {
        const columnData = toColumnMajor(fields, rows);
        return (
            <div style={{ width: '100%', overflowX: 'auto' }}>
                <Line
                    width={700}
                    height={250}
                    dataSources={{
                        primary: {
                            data: columnData,
                            meta: {},
                            requestParams: {},
                        },
                    }}
                />
            </div>
        );
    }
    if (artifact.visualization.kind === 'pie') {
        const columnData = toColumnMajor(fields, rows);
        return (
            <div style={{ width: '100%', overflowX: 'auto' }}>
                <Pie
                    width={400}
                    height={300}
                    dataSources={{
                        primary: {
                            data: columnData,
                            meta: {},
                            requestParams: {},
                        },
                    }}
                />
            </div>
        );
    }
    if (artifact.visualization.kind === 'bar') {
        const metric = firstNumericField(fields, rows);
        if (metric) {
            const values = rows.map((row) => {
                const value = toNumber(row[metric]);
                return Number.isNaN(value) ? 0 : value;
            });
            const max = Math.max(...values, 1);
            return (
                <Bars title={artifact.visualization.reason}>
                    {values.map((value, index) => (
                        <Bar key={`${metric}-${String(index)}-${String(value)}`} height={(value / max) * 100} />
                    ))}
                </Bars>
            );
        }
    }
    return <RowsTable fields={fields} rows={rows} />;
}

const SearchArtifactBody: React.FC<{ artifact: SearchArtifact; includeSpl: boolean }> = ({ artifact, includeSpl }) => {
    const previewRows = artifact.rows.slice(0, 20);
    const fields = artifact.fields.length > 0 ? artifact.fields : inferFields(previewRows);

    return (
        <>
            {artifact.status === 'pending' && (
                <SearchState $status={artifact.status}>
                    <WaitSpinner size="small" /> Dispatching search…
                </SearchState>
            )}
            {artifact.status === 'running' && (
                <SearchState $status={artifact.status}>
                    <WaitSpinner size="small" /> Search running. Preview results update automatically.
                </SearchState>
            )}
            {artifact.status === 'done' && (
                <SearchState $status={artifact.status}>Search complete. Showing final results.</SearchState>
            )}
            {artifact.status === 'error' && (
                <Message type="error">{artifact.error || 'Search failed.'}</Message>
            )}
            {artifact.browser_results_error && (
                <Message type="error">{artifact.browser_results_error}</Message>
            )}
            {(artifact.status === 'done' || (artifact.status === 'running' && previewRows.length > 0))
                && renderViz(artifact, fields, previewRows)}
            {includeSpl && (
                <SplBlock>
                    <code>{artifact.spl}</code>
                </SplBlock>
            )}
            {artifact.messages?.map((message) => (
                <Message key={message} type="info">
                    {message}
                </Message>
            ))}
        </>
    );
};

const SearchArtifactRenderer: React.FC<{ artifact: SearchArtifact; embedded?: boolean }> = ({ artifact, embedded }) => {
    const meta = (
        <Meta>
            {artifact.visualization.kind} · {artifact.status}
            {artifact.sid ? ` · SID ${artifact.sid}` : ''}
        </Meta>
    );
    const range = <Meta>{artifact.earliest} to {artifact.latest}</Meta>;

    if (embedded) {
        return (
            <EmbeddedArtifact>
                <EmbeddedMeta>
                    {meta}
                    {range}
                </EmbeddedMeta>
                <SearchArtifactBody artifact={artifact} includeSpl={false} />
            </EmbeddedArtifact>
        );
    }

    return (
        <Card>
            <Header>
                <div>
                    <Title>{artifact.title}</Title>
                    {meta}
                </div>
                {range}
            </Header>
            <Body>
                <SearchArtifactBody artifact={artifact} includeSpl />
            </Body>
        </Card>
    );
};

const ArtifactRenderer: React.FC<Props> = ({ artifact, embedded }) => {
    if (artifact.type === 'splunk_search') {
        return <SearchArtifactRenderer artifact={artifact} embedded={embedded} />;
    }
    return null;
};

export default ArtifactRenderer;
