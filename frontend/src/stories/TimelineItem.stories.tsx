import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { TimelineItem } from '../components/TimelineItem';

const meta = {
  title: 'Components/TimelineItem',
  component: TimelineItem,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof TimelineItem>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Completed: Story = {
  args: {
    title: 'Customer Context Loaded',
    description: 'Retrieved customer profile and order history.',
    timestamp: '2024-03-15 10:23:45',
    status: 'completed',
  },
};

export const Pending: Story = {
  args: {
    title: 'Processing Refund',
    description: 'Checking refund eligibility and initiating transaction.',
    timestamp: '2024-03-15 10:24:12',
    status: 'pending',
  },
};

export const Failed: Story = {
  args: {
    title: 'Refund Eligibility Check',
    description: 'Failed to verify refund window. Requires manual review.',
    timestamp: '2024-03-15 10:25:00',
    status: 'failed',
  },
};

export const WithoutTimestamp: Story = {
  args: {
    title: 'Ticket Escalated',
    description: 'Escalated to human support team.',
    status: 'completed',
  },
};
