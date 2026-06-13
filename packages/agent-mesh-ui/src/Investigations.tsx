import React, { useCallback, useEffect, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import Modal from '@splunk/react-ui/Modal';
import {
    StyledAppContainer,
    StyledConsoleActions,
    StyledConsoleControls,
    StyledConsoleMain,
    StyledConsoleMeta,
    StyledConsoleTitle,
    StyledConsoleTitleGroup,
    StyledModalContent,
    StyledPanelFill,
} from './InvestigationsStyles';
import InvestigationPage, { ConsoleChromeState } from './pages/InvestigationPage';
import SettingsPage from './pages/SettingsPage';
import AboutPage from './pages/AboutPage';
import HistorySidebar from './components/HistorySidebar';

type Overlay = 'settings' | 'about' | null;

const Investigations: React.FC = () => {
    const containerRef = useRef<HTMLDivElement>(null);
    const settingsButtonRef = useRef<HTMLButtonElement | HTMLAnchorElement | null>(null);
    const aboutButtonRef = useRef<HTMLButtonElement | HTMLAnchorElement | null>(null);
    const [shellHeight, setShellHeight] = useState<number>();
    const [overlay, setOverlay] = useState<Overlay>(null);
    const [loadInvestigationId, setLoadInvestigationId] = useState<string | null>(null);
    const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
    const [consoleChrome, setConsoleChrome] = useState<ConsoleChromeState>({
        status: null,
        owner: null,
        id: null,
        isDemo: false,
        canClear: false,
        onClear: null,
    });

    useEffect(() => {
        const updateShellHeight = () => {
            const top = containerRef.current?.getBoundingClientRect().top ?? 0;
            setShellHeight(Math.max(480, window.innerHeight - top));
        };

        updateShellHeight();
        window.addEventListener('resize', updateShellHeight);
        return () => window.removeEventListener('resize', updateShellHeight);
    }, []);

    const closeOverlay = () => setOverlay(null);

    const handleSidebarSelect = useCallback((investigationId: string) => {
        setLoadInvestigationId(investigationId);
    }, []);

    const handleInvestigationStarted = useCallback(() => {
        setSidebarRefreshKey((prev) => prev + 1);
    }, []);

    const consoleMeta = [
        consoleChrome.status,
        consoleChrome.owner,
        consoleChrome.id,
    ].filter(Boolean).join(' · ');

    return (
        <StyledAppContainer ref={containerRef} $height={shellHeight} data-testid="investigations-shell">
            <StyledConsoleControls aria-label="Console controls">
                <StyledConsoleTitleGroup>
                    <StyledConsoleTitle>Investigation Console</StyledConsoleTitle>
                    {consoleChrome.isDemo && <StyledConsoleMeta>Demo data</StyledConsoleMeta>}
                    {consoleMeta && <StyledConsoleMeta>{consoleMeta}</StyledConsoleMeta>}
                </StyledConsoleTitleGroup>
                <StyledConsoleActions>
                    {consoleChrome.canClear && (
                        <Button label="Clear" appearance="subtle" onClick={() => consoleChrome.onClear?.()} />
                    )}
                    <Button
                        appearance="secondary"
                        elementRef={settingsButtonRef}
                        icon={<span aria-hidden="true">⚙</span>}
                        label="Settings"
                        onClick={() => setOverlay('settings')}
                    />
                    <Button
                        appearance="subtle"
                        elementRef={aboutButtonRef}
                        icon={<span aria-hidden="true">i</span>}
                        label="About"
                        onClick={() => setOverlay('about')}
                    />
                </StyledConsoleActions>
            </StyledConsoleControls>
            <StyledConsoleMain>
                <HistorySidebar
                    activeInvestigationId={consoleChrome.id}
                    onSelect={handleSidebarSelect}
                    refreshKey={sidebarRefreshKey}
                />
                <StyledPanelFill>
                    <InvestigationPage
                        onConsoleChromeChange={setConsoleChrome}
                        loadInvestigationId={loadInvestigationId}
                        onInvestigationStarted={handleInvestigationStarted}
                    />
                </StyledPanelFill>
            </StyledConsoleMain>
            <Modal
                divider="both"
                initialFocus="container"
                onRequestClose={closeOverlay}
                open={overlay === 'settings'}
                returnFocus={settingsButtonRef}
                style={{ width: '720px' }}
            >
                <StyledModalContent>
                    <Modal.Header title="Settings" subtitle="Configure the LLM provider used by the harness." />
                    <Modal.Body style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' }}>
                        <SettingsPage />
                    </Modal.Body>
                </StyledModalContent>
            </Modal>
            <Modal
                closeOnClickAway
                divider="both"
                initialFocus="container"
                onRequestClose={closeOverlay}
                open={overlay === 'about'}
                returnFocus={aboutButtonRef}
                style={{ width: '760px' }}
            >
                <StyledModalContent>
                    <Modal.Header title="About Splunk Agent Mesh" subtitle="Agentic SOC investigation console." />
                    <Modal.Body style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' }}>
                        <AboutPage />
                    </Modal.Body>
                </StyledModalContent>
            </Modal>
        </StyledAppContainer>
    );
};

export default Investigations;
