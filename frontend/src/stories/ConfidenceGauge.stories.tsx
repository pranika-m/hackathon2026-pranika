import type { Meta, StoryObj } from '@storybook/nextjs-vite';
import { ConfidenceGauge } from '../components/ConfidenceGauge';

const meta = {
  title: 'Components/ConfidenceGauge',
  component: ConfidenceGauge,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof ConfidenceGauge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const HighConfidence: Story = {
  args: {
    score: 0.95,
    label: 'Resolution Confidence',
  },
};

export const MediumConfidence: Story = {
  args: {
    score: 0.65,
    label: 'Resolution Confidence',
  },
};

export const LowConfidence: Story = {
  args: {
    score: 0.35,
    label: 'Resolution Confidence',
  },
};

export const VeryLow: Story = {
  args: {
    score: 0.1,
    label: 'Resolution Confidence',
  },
};
