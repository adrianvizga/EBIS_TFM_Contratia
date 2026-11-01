import { describe, it, expect } from 'vitest';
import { render, act } from '@testing-library/react';
import { NotificationsProvider } from '../../../context/NotificationsContext';
import { useNotifications } from '../../../context/useNotifications';

function TestConsumer({ onContext }: { onContext: (ctx: ReturnType<typeof useNotifications>) => void }) {
  const ctx = useNotifications();
  onContext(ctx);
  return null;
}

describe('NotificationsContext', () => {
  it('initial_trigger_is_zero — refreshTrigger starts at 0', () => {
    let ctx: ReturnType<typeof useNotifications> | null = null;
    render(
      <NotificationsProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </NotificationsProvider>,
    );

    expect(ctx!.refreshTrigger).toBe(0);
  });

  it('refresh_increments_trigger — refreshNotifications() increments the trigger', () => {
    let ctx: ReturnType<typeof useNotifications> | null = null;
    render(
      <NotificationsProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </NotificationsProvider>,
    );

    act(() => {
      ctx!.refreshNotifications();
    });
    expect(ctx!.refreshTrigger).toBe(1);

    act(() => {
      ctx!.refreshNotifications();
    });
    expect(ctx!.refreshTrigger).toBe(2);
  });

  it('throws_outside_provider — useNotifications throws when used outside provider', () => {
    const Faulty = () => {
      useNotifications();
      return null;
    };

    expect(() => render(<Faulty />)).toThrow(
      'useNotifications must be used within a NotificationsProvider',
    );
  });
});
