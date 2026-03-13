import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BatteryBar } from '../components/common/BatteryBar';
import { StatusBadge } from '../components/common/StatusBadge';

describe('StatusBadge', () => {
  it('renders CLEANING label', () => {
    render(<StatusBadge status="CLEANING" />);
    expect(screen.getByText('掃除中')).toBeInTheDocument();
  });

  it('renders ERROR label', () => {
    render(<StatusBadge status="ERROR" />);
    expect(screen.getByText('エラー')).toBeInTheDocument();
  });

  it('renders LOW_BATTERY label', () => {
    render(<StatusBadge status="LOW_BATTERY" />);
    expect(screen.getByText('低バッテリー')).toBeInTheDocument();
  });

  it('renders CHARGING label', () => {
    render(<StatusBadge status="CHARGING" />);
    expect(screen.getByText('充電中')).toBeInTheDocument();
  });
});

describe('BatteryBar', () => {
  it('shows percentage label', () => {
    render(<BatteryBar level={75} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('hides label when showLabel=false', () => {
    render(<BatteryBar level={50} showLabel={false} />);
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('renders with 0% battery', () => {
    render(<BatteryBar level={0} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });
});
