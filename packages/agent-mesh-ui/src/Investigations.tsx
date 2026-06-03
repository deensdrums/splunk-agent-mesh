import React, { useEffect, useRef, useState } from 'react';
import TabLayout from '@splunk/react-ui/TabLayout';
import { StyledAppContainer, StyledNavigationShell, StyledPanelFill } from './InvestigationsStyles';
import InvestigationPage from './pages/InvestigationPage';
import SettingsPage from './pages/SettingsPage';
import AboutPage from './pages/AboutPage';

type Tab = 'investigation' | 'settings' | 'about';

const Investigations: React.FC = () => {
    const [activeTab, setActiveTab] = useState<Tab>('investigation');
    const containerRef = useRef<HTMLDivElement>(null);
    const [shellHeight, setShellHeight] = useState<number>();

    useEffect(() => {
        const updateShellHeight = () => {
            const top = containerRef.current?.getBoundingClientRect().top ?? 0;
            setShellHeight(Math.max(480, window.innerHeight - top));
        };

        updateShellHeight();
        window.addEventListener('resize', updateShellHeight);
        return () => window.removeEventListener('resize', updateShellHeight);
    }, []);

    return (
        <StyledAppContainer ref={containerRef} $height={shellHeight} data-testid="investigations-shell">
            <StyledNavigationShell>
                <TabLayout
                    activePanelId={activeTab}
                    onChange={(_e: unknown, { activePanelId }: { activePanelId?: string }) => {
                        if (activePanelId) {setActiveTab(activePanelId as Tab);}
                    }}
                >
                    <TabLayout.Panel label="Investigation" panelId="investigation">
                        <StyledPanelFill>
                            <InvestigationPage />
                        </StyledPanelFill>
                    </TabLayout.Panel>
                    <TabLayout.Panel label="Settings" panelId="settings">
                        <SettingsPage />
                    </TabLayout.Panel>
                    <TabLayout.Panel label="About" panelId="about">
                        <AboutPage />
                    </TabLayout.Panel>
                </TabLayout>
            </StyledNavigationShell>
        </StyledAppContainer>
    );
};

export default Investigations;
