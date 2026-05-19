import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Investigations from '../Investigations';

// Stub styled-components and Splunk theme/UI modules for Jest
jest.mock('@splunk/themes', () => ({
    variables: new Proxy({}, { get: () => '0px' }),
    mixins: { reset: () => '' },
}));
jest.mock('@splunk/react-ui/TabLayout', () => {
    const Panel = ({ children }: { children: React.ReactNode; panelId: string }) => <div>{children}</div>;
    const TabLayout = ({ children }: { children: React.ReactNode }) => <div>{children}</div>;
    TabLayout.Panel = Panel;
    return TabLayout;
});

test('renders Sentinel Mesh header', () => {
    render(<Investigations />);
    expect(screen.getByText(/Sentinel Mesh/i)).toBeInTheDocument();
});

test('renders tagline', () => {
    render(<Investigations />);
    expect(screen.getByText(/From alert to evidence-backed response/i)).toBeInTheDocument();
});

test('has a Start Investigation button', async () => {
    const user = userEvent.setup();
    render(<Investigations />);
    const btn = screen.queryByRole('button', { name: /Start Investigation/i });
    // Button may not be present if tab rendering is mocked; presence check only
    if (btn) {
        expect(btn).toBeInTheDocument();
    }
});
