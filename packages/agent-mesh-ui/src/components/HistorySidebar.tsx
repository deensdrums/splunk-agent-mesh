import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { variables } from '@splunk/themes';
import WaitSpinner from '@splunk/react-ui/WaitSpinner';
import { InvestigationSummary } from '../types';
import { apiClient } from '../services/apiClient';

interface Props {
    activeInvestigationId: string | null;
    onSelect: (investigationId: string) => void;
    refreshKey?: number;
}

const COLLAPSED_WIDTH = '40px';
const EXPANDED_WIDTH = '280px';

const Rail = styled.div<{ $expanded: boolean }>`
    display: flex;
    flex-direction: column;
    flex: 0 0 ${({ $expanded }) => ($expanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH)};
    width: ${({ $expanded }) => ($expanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH)};
    min-width: ${({ $expanded }) => ($expanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH)};
    height: 100%;
    box-sizing: border-box;
    border-right: 1px solid ${variables.borderColor};
    background: ${variables.backgroundColorNavigation};
    overflow: hidden;
    transition: flex-basis 150ms ease, width 150ms ease, min-width 150ms ease;
`;

const ToggleButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    width: 100%;
    height: 36px;
    border: none;
    border-bottom: 1px solid ${variables.borderColor};
    background: transparent;
    color: ${variables.contentColorDefault};
    font-size: 16px;
    cursor: pointer;

    &:hover {
        background: ${variables.backgroundColorHover};
    }
`;

const SidebarHeader = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: ${variables.spacingSmall} ${variables.spacingSmall} ${variables.spacingSmall} ${variables.spacingMedium};
    border-bottom: 1px solid ${variables.borderColor};
    flex: 0 0 auto;
`;

const SidebarTitle = styled.div`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
    text-transform: uppercase;
    letter-spacing: 0.06em;
`;

const CloseButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: ${variables.contentColorMuted};
    font-size: 14px;
    cursor: pointer;

    &:hover {
        background: ${variables.backgroundColorHover};
    }
`;

const ItemList = styled.div`
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    padding: ${variables.spacingXSmall} 0;
`;

const Item = styled.button<{ $active: boolean }>`
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
    box-sizing: border-box;
    padding: ${variables.spacingSmall} ${variables.spacingMedium};
    border: none;
    border-left: 3px solid ${({ $active }) => ($active ? variables.interactiveColorPrimary : 'transparent')};
    background: ${({ $active }) => ($active ? variables.backgroundColorHover : 'transparent')};
    text-align: left;
    cursor: pointer;

    &:hover {
        background: ${variables.backgroundColorHover};
    }
`;

const ItemTitle = styled.div`
    font-size: ${variables.fontSizeSmall};
    font-weight: ${variables.fontWeightSemiBold};
    color: ${variables.contentColorActive};
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
`;

const ItemMeta = styled.div`
    display: flex;
    align-items: center;
    gap: ${variables.spacingXSmall};
    font-size: 11px;
    color: ${variables.contentColorMuted};
`;

const StatusDot = styled.span<{ $status: string }>`
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex: 0 0 auto;
    background: ${({ $status }) => {
        switch ($status) {
            case 'complete': return variables.statusColorLow;
            case 'running': case 'pending': return variables.statusColorInfo;
            case 'error': return variables.statusColorHigh;
            default: return variables.contentColorMuted;
        }
    }};
`;

const EmptyMessage = styled.div`
    padding: ${variables.spacingLarge} ${variables.spacingMedium};
    color: ${variables.contentColorMuted};
    font-size: ${variables.fontSizeSmall};
    text-align: center;
    font-style: italic;
`;

const LoadingState = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    padding: ${variables.spacingLarge};
`;

function relativeTime(isoString: string | null): string {
    if (!isoString) {
        return '';
    }
    const then = new Date(isoString).getTime();
    const now = Date.now();
    const seconds = Math.floor((now - then) / 1000);
    if (seconds < 60) {
        return 'just now';
    }
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) {
        return `${minutes}m ago`;
    }
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours}h ago`;
    }
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

const HistorySidebar: React.FC<Props> = ({ activeInvestigationId, onSelect, refreshKey }) => {
    const [expanded, setExpanded] = useState(false);
    const [items, setItems] = useState<InvestigationSummary[]>([]);
    const [loading, setLoading] = useState(false);
    const [fetched, setFetched] = useState(false);

    useEffect(() => {
        if (!expanded) {
            return;
        }
        setLoading(true);
        apiClient
            .listInvestigations()
            .then((res) => {
                setItems(res.investigations);
                setFetched(true);
                setLoading(false);
            })
            .catch(() => {
                setItems([]);
                setFetched(true);
                setLoading(false);
            });
    }, [expanded, refreshKey]);

    if (!expanded) {
        return (
            <Rail $expanded={false}>
                <ToggleButton
                    onClick={() => setExpanded(true)}
                    title="Show investigation history"
                    aria-label="Show investigation history"
                >
                    &#x23F2;
                </ToggleButton>
            </Rail>
        );
    }

    return (
        <Rail $expanded data-testid="history-sidebar">
            <SidebarHeader>
                <SidebarTitle>History</SidebarTitle>
                <CloseButton
                    onClick={() => setExpanded(false)}
                    title="Close history"
                    aria-label="Close history"
                >
                    &#x2715;
                </CloseButton>
            </SidebarHeader>
            <ItemList>
                {loading && (
                    <LoadingState>
                        <WaitSpinner size="small" />
                    </LoadingState>
                )}
                {!loading && fetched && items.length === 0 && (
                    <EmptyMessage>No investigations yet.</EmptyMessage>
                )}
                {!loading &&
                    items.map((item) => (
                        <Item
                            key={item.investigation_id}
                            $active={item.investigation_id === activeInvestigationId}
                            onClick={() => onSelect(item.investigation_id)}
                            title={item.title || item.investigation_id}
                        >
                            <ItemTitle>{item.title || item.investigation_id}</ItemTitle>
                            <ItemMeta>
                                <StatusDot $status={item.status} />
                                <span>{item.status}</span>
                                <span>{relativeTime(item.updated_at)}</span>
                            </ItemMeta>
                        </Item>
                    ))}
            </ItemList>
        </Rail>
    );
};

export default HistorySidebar;
