import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AnalyzeContract from '../../../components/sections/AnalyzeContract';

const controller = { loading: false };
vi.mock('../../../components/sections/analyzeContract/useAnalyzeContractController', () => ({
  useAnalyzeContractController: () => controller,
}));
vi.mock('../../../components/sections/analyzeContract/AnalyzeContractView', () => ({
  AnalyzeContractView: (props: { loading: boolean }) => <div data-testid="analysis-view">{props.loading ? 'invalid' : 'connected'}</div>,
}));

describe('AnalyzeContract composition', () => {
  it('connects the controller to the presentational view', () => {
    render(<AnalyzeContract />);
    expect(screen.getByTestId('analysis-view')).toHaveTextContent('connected');
  });
});
