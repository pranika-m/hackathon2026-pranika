import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { TicketRow } from '../components/TicketRow';

const meta = {
  title: 'Components/TicketRow',
  component: TicketRow,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof TicketRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Pending: Story = {
  args: {
    ticketId: 'TKT-001',
    subject: 'Damaged item arrived',
    customer: 'John Doe',
    status: 'pending',
    priority: 'high',
  },
};

export const Resolved: Story = {
  args: {
    ticketId: 'TKT-002',
    subject: 'Refund processed successfully',
    customer: 'Jane Smith',
    status: 'resolved',
    priority: 'medium',
  },
};

export const Escalated: Story = {
  args: {
    ticketId: 'TKT-003',
    subject: 'Conflicting data detected',
    customer: 'Robert Johnson',
    status: 'escalated',
    priority: 'urgent',
  },
};

export const LowPriority: Story = {
  args: {
    ticketId: 'TKT-004',
    subject: 'General inquiry about product',
    customer: 'Alice Brown',
    status: 'pending',
    priority: 'low',
  },
};
