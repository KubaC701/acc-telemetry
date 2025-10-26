import { useQuery } from '@tanstack/react-query';
import { jobsApi } from '../lib/api';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { ProgressBar } from './ui/ProgressBar';

interface JobStatusProps {
  jobId: string;
  onComplete?: () => void;
}

export function JobStatus({ jobId, onComplete }: JobStatusProps) {
  const { data: job, isLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.getStatus(jobId),
    refetchInterval: (data) => {
      // Stop polling if job is completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        if (data?.status === 'completed') {
          onComplete?.();
        }
        return false;
      }
      return 1000; // Poll every second while processing
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <svg className="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!job) {
    return null;
  }

  const getStatusColor = () => {
    switch (job.status) {
      case 'completed':
        return 'bg-green-50 border-green-200';
      case 'failed':
        return 'bg-red-50 border-red-200';
      case 'processing':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed':
        return (
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'processing':
        return (
          <svg className="animate-spin w-5 h-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <Card className={`border-2 ${getStatusColor()}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Processing Status</CardTitle>
          {getStatusIcon()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium text-gray-700">Video: {job.video_name}</p>
          <p className="text-sm text-gray-600">Job ID: {job.job_id}</p>
        </div>

        {job.status === 'processing' && (
          <ProgressBar value={job.progress} showPercentage />
        )}

        <div className={`p-3 rounded-lg ${
          job.status === 'completed' ? 'bg-green-100' :
          job.status === 'failed' ? 'bg-red-100' :
          'bg-blue-100'
        }`}>
          <p className={`text-sm font-medium ${
            job.status === 'completed' ? 'text-green-800' :
            job.status === 'failed' ? 'text-red-800' :
            'text-blue-800'
          }`}>
            {job.message}
          </p>
        </div>

        {job.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-800">Error: {job.error}</p>
          </div>
        )}

        <div className="text-xs text-gray-500">
          <p>Started: {new Date(job.created_at).toLocaleString()}</p>
          {job.completed_at && (
            <p>Completed: {new Date(job.completed_at).toLocaleString()}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function JobsList() {
  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: jobsApi.list,
    refetchInterval: 2000, // Poll every 2 seconds
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <div className="flex items-center justify-center py-4">
            <svg className="animate-spin h-6 w-6 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!jobs || jobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 text-center py-4">No jobs yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Jobs ({jobs.length})</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {jobs.slice(0, 5).map((job) => (
          <div
            key={job.job_id}
            className="border rounded-lg p-3 space-y-2"
          >
            <div className="flex items-center justify-between">
              <p className="font-medium text-sm">{job.video_name}</p>
              <span className={`px-2 py-1 text-xs rounded-full ${
                job.status === 'completed' ? 'bg-green-100 text-green-800' :
                job.status === 'failed' ? 'bg-red-100 text-red-800' :
                job.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {job.status}
              </span>
            </div>

            {job.status === 'processing' && (
              <ProgressBar value={job.progress} showPercentage={false} className="mt-2" />
            )}

            <p className="text-xs text-gray-600">{job.message}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
