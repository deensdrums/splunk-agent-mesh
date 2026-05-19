import React, { useState } from 'react';
import TabLayout from '@splunk/react-ui/TabLayout';
import { StyledAppContainer, StyledHeader, StyledTagline } from './InvestigationsStyles';
import InvestigationPage from './pages/InvestigationPage';
import SettingsPage from './pages/SettingsPage';
import AboutPage from './pages/AboutPage';

type Tab = 'investigation' | 'settings' | 'about';

const Investigations: React.FC = () => {
    const [activeTab, setActiveTab] = useState<Tab>('investigation');

    return (
        <StyledAppContainer>
            <StyledHeader>Sentinel Mesh</StyledHeader>
            <StyledTagline>From alert to evidence-backed response in minutes.</StyledTagline>
            <TabLayout
                activePanelId={activeTab}
                onChange={(_e: unknown, { activePanelId }: { activePanelId?: string }) => {
                    if (activePanelId) setActiveTab(activePanelId as Tab);
                }}
            >
                <TabLayout.Panel label="Investigation" panelId="investigation">
                    <InvestigationPage />
                </TabLayout.Panel>
                <TabLayout.Panel label="Settings" panelId="settings">
                    <SettingsPage />
                </TabLayout.Panel>
                <TabLayout.Panel label="About" panelId="about">
                    <AboutPage />
                </TabLayout.Panel>
            </TabLayout>
        </StyledAppContainer>
    );
};

export default Investigations;
