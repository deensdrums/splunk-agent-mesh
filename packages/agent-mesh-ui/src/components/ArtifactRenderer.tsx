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

const SearchArtifactRenderer: React.FC<{ artifact: SearchArtifact }> = ({ artifact }) => {
    const previewRows = artifact.rows.slice(0, 20);
    const fields = artifact.fields.length > 0 ? artifact.fields : inferFields(previewRows);

    return (
        <Card>
            <Header>
                <div>
                    <Title>{artifact.title}</Title>
                    <Meta>
                        {artifact.visualization.kind} · {artifact.status}
                        {artifact.sid ? ` · SID ${artifact.sid}` : ''}
                    </Meta>
                </div>
                <Meta>
                    {artifact.earliest} to {artifact.latest}
                </Meta>
            </Header>
            <Body>
                {artifact.status === 'running' && (
                    <Message type="info">
                        <WaitSpinner size="small" /> Search is still running.
                    </Message>
                )}
                {artifact.status === 'error' && (
                    <Message type="error">{artifact.error || 'Search failed.'}</Message>
                )}
                {artifact.status === 'done' && renderViz(artifact, fields, previewRows)}
                <SplBlock>
                    <code>{artifact.spl}</code>
                </SplBlock>
                {artifact.messages?.map((message) => (
                    <Message key={message} type="info">
                        {message}
                    </Message>
                ))}
            </Body>
        </Card>
    );
};

const ArtifactRenderer: React.FC<Props> = ({ artifact }) => {
    if (artifact.type === 'splunk_search') {
        return <SearchArtifactRenderer artifact={artifact} />;
    }
    return null;
};

export default ArtifactRenderer;
