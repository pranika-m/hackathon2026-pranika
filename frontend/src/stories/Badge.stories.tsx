import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { Badge } from '../components/Badge';

const meta = {
  title: 'Components/Badge',
  component: Badge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    label: 'Pending',
  },
};

export const Success: Story = {
  args: {
    label: 'Resolved',
    variant: 'success',
  },
};

export const Warning: Story = {
  args: {
    label: 'In Progress',
    variant: 'warning',
  },
};

export const Error: Story = {
  args: {
    label: 'Failed',
    variant: 'error',
  },
};

export const Info: Story = {
  args: {
    label: 'Escalated',
    variant: 'info',
  },
};
