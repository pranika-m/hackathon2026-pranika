import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { SummaryCard } from '../components/SummaryCard';

const meta = {
  title: 'Components/SummaryCard',
  component: SummaryCard,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof SummaryCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    title: 'Resolution Summary',
    content: 'The customer reported a damaged item. We verified the damage and issued a full refund.',
  },
};

export const LowPriority: Story = {
  args: {
    title: 'General Inquiry',
    content: 'Customer asked about product availability.',
    priority: 'low',
  },
};

export const HighPriority: Story = {
  args: {
    title: 'Escalation Notice',
    content: 'High-value customer with unresolved issue. Requires immediate attention.',
    priority: 'high',
  },
};

export const UrgentPriority: Story = {
  args: {
    title: 'Critical Issue',
    content: 'Customer threatening legal action. Legal review required.',
    priority: 'urgent',
  },
};
