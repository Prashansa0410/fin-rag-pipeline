"use client";
import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

export default function ReviewDetail() {
  const { id } = useParams();
  const router = useRouter();
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editedAnswer, setEditedAnswer] = useState("");

  useEffect(() => {
    fetch(`/api/reviews/${id}`)
      .then(res => res.json())
      .then(data => {
        setReview(data);
        setEditedAnswer(data.original_answer);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching review", err);
        setLoading(false);
      });
  }, [id]);

  const handleAction = async (decision: string) => {
    try {
      await fetch(`/api/reviews/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: "demo-user", // Hardcoded for demo
          decision,
          edited_answer: decision === 'EDIT' ? editedAnswer : undefined
        })
      });
      router.push('/review');
    } catch (error) {
      console.error("Failed to perform action", error);
    }
  };

  if (loading) return <div className="p-8">Loading review details...</div>;
  if (!review) return <div className="p-8 text-red-500">Review not found</div>;

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Left Pane - Editor */}
      <div className="w-1/2 p-6 flex flex-col border-r border-gray-200 bg-white shadow-sm overflow-y-auto">
        <div className="mb-4">
          <button onClick={() => router.push('/review')} className="text-sm text-blue-600 mb-2 block hover:underline">
            &larr; Back to Queue
          </button>
          <h1 className="text-2xl font-bold text-gray-800">Review Query</h1>
          <p className="mt-2 text-lg text-gray-700 bg-gray-100 p-3 rounded">{review.query_text}</p>
        </div>
        
        <div className="flex gap-4 mb-4 text-xs">
          <div className="bg-gray-100 p-2 rounded border border-gray-200">
            <span className="font-semibold block text-gray-500 uppercase">Confidence</span>
            <span className={review.retrieval_confidence_level === 'HIGH' ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
              {review.retrieval_confidence_level} ({(review.retrieval_confidence * 100).toFixed(1)}%)
            </span>
          </div>
          <div className="bg-gray-100 p-2 rounded border border-gray-200">
            <span className="font-semibold block text-gray-500 uppercase">Conflict Detected</span>
            <span className={review.conflicting_evidence ? 'text-red-600 font-bold' : 'text-green-600 font-bold'}>
              {review.conflicting_evidence ? 'YES' : 'NO'}
            </span>
          </div>
          <div className="bg-gray-100 p-2 rounded border border-gray-200">
            <span className="font-semibold block text-gray-500 uppercase">Latency (Total)</span>
            <span className="font-bold">{review.metrics?.total_latency_ms} ms</span>
          </div>
        </div>
        
        <div className="flex-1 flex flex-col">
          <label className="font-semibold text-gray-700 mb-2">Generated Answer (Editable)</label>
          <textarea 
            className="flex-1 w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none font-sans leading-relaxed text-gray-800"
            value={editedAnswer}
            onChange={(e) => setEditedAnswer(e.target.value)}
          />
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button 
            onClick={() => handleAction('REJECT')}
            className="px-6 py-2 bg-red-100 text-red-700 font-semibold rounded-lg hover:bg-red-200 transition"
          >
            Reject
          </button>
          <button 
            onClick={() => handleAction(editedAnswer === review.original_answer ? 'APPROVE' : 'EDIT')}
            className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
          >
            {editedAnswer === review.original_answer ? 'Approve As Is' : 'Save & Approve Edit'}
          </button>
        </div>
      </div>

      {/* Right Pane - Evidence */}
      <div className="w-1/2 p-6 overflow-y-auto bg-gray-50">
        <h2 className="text-xl font-bold text-gray-800 mb-4 border-b pb-2">Retrieved Evidence</h2>
        <div className="space-y-4">
          {/* For the demo, we assume evidence chunks would be passed in the API. 
              Since they aren't directly saved on the review model yet, we'll render a placeholder.
              In full implementation, these would be fetched via a /api/research/{id}/chunks endpoint. */}
          <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-bold text-blue-700">Source: Settlement_Policy_2026.pdf (Page 4)</span>
              <span className="text-xs font-semibold bg-green-100 text-green-800 px-2 py-1 rounded">Score: 0.92</span>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">
              ...Partner A utilizes a standard T+1 settlement window for all North American equities. However, under compliance rule 402(b), reconciliation exceptions must be flagged if...
            </p>
          </div>
          <div className="p-4 bg-white border border-red-200 rounded-lg shadow-sm">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-bold text-red-700">Source: Legacy_Ops_Manual.pdf (Page 12)</span>
              <span className="text-xs font-semibold bg-yellow-100 text-yellow-800 px-2 py-1 rounded">Score: 0.88</span>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed">
              ...All partners default to a T+2 settlement window. Any deviations require manual override...
            </p>
            <div className="mt-2 text-xs text-red-600 font-bold flex items-center">
              ⚠️ Warning: Conflicting rule detected against primary source.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
