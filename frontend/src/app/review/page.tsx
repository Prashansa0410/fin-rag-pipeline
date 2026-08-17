"use client";
import React, { useEffect, useState } from 'react';
import Link from 'next/link';

interface ReviewItem {
  review_id: string;
  query_text: string;
  query_type: string;
  retrieval_confidence: number;
  retrieval_confidence_level: string;
  conflicting_evidence: boolean;
  model_tier: string;
  created_at: string;
}

export default function ReviewDashboard() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/reviews/pending')
      .then(res => res.json())
      .then(data => {
        setReviews(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching reviews", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-8">Loading pending reviews...</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Human Review Queue</h1>
      {reviews.length === 0 ? (
        <p className="text-gray-500">No pending reviews.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg shadow">
          <table className="min-w-full divide-y divide-gray-200 bg-white">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Query</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Conflict</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tier</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {reviews.map(review => (
                <tr key={review.review_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 truncate max-w-xs">{review.query_text}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{review.query_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      ${review.retrieval_confidence_level === 'HIGH' ? 'bg-green-100 text-green-800' : 
                        review.retrieval_confidence_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 
                        'bg-red-100 text-red-800'}`}>
                      {review.retrieval_confidence_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {review.conflicting_evidence ? <span className="text-red-600 font-bold">YES</span> : "No"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{review.model_tier}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link href={`/review/${review.review_id}`} className="text-blue-600 hover:text-blue-900">
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
