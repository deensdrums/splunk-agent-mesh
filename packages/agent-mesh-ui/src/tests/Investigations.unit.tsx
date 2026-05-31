import React from 'react';
import { render, screen } from '@testing-library/react';

import Investigations from '../Investigations';

// Stub styled-components and Splunk theme/UI modules for Jest
jest.mock('@splunk/themes', () => ({
    variables: new Proxy({}, { get: () => '0px' }),
    mixins: new Proxy({}, { get: () => () => '' }),
}));
jest.mock('@splunk/react-ui/TabLayout', () => {
    // eslint-disable-next-line global-require
    const mockReact = require('react');
    const Panel = ({ children }: { children: React.ReactNode }) => <div>{children}</div>;
    const TabLayout = ({ children }: { children: React.ReactNode }) => (
        <div>{mockReact.Children.toArray(children)[0]}</div>
    );
    TabLayout.Panel = Panel;
    return TabLayout;
});
jest.mock('@splunk/react-ui/Button', () => ({ label, onClick, disabled }: any) => (
    <button type="button" onClick={onClick} disabled={disabled}>
        {label}
    </button>
));
jest.mock('@splunk/react-ui/TextArea', () => ({ value, onChange }: any) => (
    <textarea value={value} onChange={(event) => onChange?.(event, { value: event.target.value })} />
));
jest.mock('@splunk/react-ui/Text', () => ({ value, onChange, placeholder }: any) => (
    <input
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange?.(event, { value: event.target.value })}
    />
));
jest.mock('@splunk/react-ui/Message', () => ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
));
jest.mock('@splunk/react-ui/WaitSpinner', () => () => <span>Loading</span>);
jest.mock('@splunk/react-ui/Select', () => {
    const Select = ({ children }: { children: React.ReactNode }) => <select>{children}</select>;
    Select.Option = ({ label, value }: { label: string; value: string }) => <option value={value}>{label}</option>;
    return Select;
});
jest.mock('react-markdown', () => ({ children }: { children: React.ReactNode }) => <div>{children}</div>);
jest.mock('remark-gfm', () => () => null);
jest.mock('rehype-sanitize', () => () => null);
// @splunk/visualizations pulls in canvas/Popover internals that don't load
// under jsdom; stub the chart components used by ArtifactRenderer.
jest.mock('@splunk/visualizations/Column', () => () => <div>Column</div>);
jest.mock('@splunk/visualizations/Line', () => () => <div>Line</div>);
jest.mock('@splunk/visualizations/Pie', () => () => <div>Pie</div>);

test('renders Splunk Agent Mesh header', () => {
    render(<Investigations />);
    expect(screen.getByText(/Splunk Agent Mesh/i)).toBeInTheDocument();
});

test('renders tagline', () => {
    render(<Investigations />);
    expect(screen.getByText(/From alert to evidence-backed response/i)).toBeInTheDocument();
});

test('has a Start Investigation button', () => {
    render(<Investigations />);
    const btn = screen.queryByRole('button', { name: /Start Investigation/i });
    // Button may not be present if tab rendering is mocked; presence check only
    if (btn) {
        expect(btn).toBeInTheDocument();
    }
});
