import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToast } from '../components/Toast';
import Navbar from '../components/Navbar';
import {
  getTaskSchedule,
  submitSchedule,
  confirmSchedule,
} from '../services/api';

type Step = 'form' | 'review' | 'confirmed';

export default function ScheduleTaskPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const taskId = parseInt(id || '0');

  const [step, setStep] = useState<Step>('form');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Form data from API
  const [scheduleData, setScheduleData] = useState<any>(null);

  // Form fields
  const [scheduledDate, setScheduledDate] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [department, setDepartment] = useState('');
  const [priority, setPriority] = useState('medium');
  const [notes, setNotes] = useState('');
  const [meetingType, setMeetingType] = useState('standard');

  // Conditional fields
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [location, setLocation] = useState('');
  const [roomNumber, setRoomNumber] = useState('');
  const [duration, setDuration] = useState('60');
  const [participants, setParticipants] = useState('');

  // Review state
  const [reviewData, setReviewData] = useState<any>(null);
  const [confirmationId, setConfirmationId] = useState('');
  const [confirmUrl, setConfirmUrl] = useState('');

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  useEffect(() => {
    if (!taskId) return;
    getTaskSchedule(taskId)
      .then((data) => {
        setScheduleData(data);
        if (data.availableSlots.length > 0) {
          setScheduledDate(data.availableSlots[0].date);
          setScheduledTime(data.availableSlots[0].times[0]);
        }
        if (data.departments.length > 0) {
          setDepartment(data.departments[0]);
        }
      })
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [taskId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const payload: Record<string, unknown> = {
        assigneeId: user.id,
        department,
        priority,
        submittedAt: new Date().toISOString(),
        scheduledDate,
        scheduledTime,
        projectCode: scheduleData?.projectCode || '',
        notes: notes || undefined,
        meetingType,
        _csrf: scheduleData._csrf,
        _formId: scheduleData._formId,
      };

      // Add conditional fields based on meeting type
      if (meetingType === 'video_call' || meetingType === 'workshop') {
        payload.contactName = contactName;
        payload.contactEmail = contactEmail;
      }
      if (meetingType === 'in_person') {
        payload.location = location;
        payload.roomNumber = roomNumber;
      }
      if (meetingType === 'workshop') {
        payload.duration = duration;
        payload.participants = participants;
      }

      const result = await submitSchedule(taskId, payload);
      setConfirmationId(result.confirmationId);
      setReviewData(result.reviewData);
      setStep('review');
      addToast('Schedule submitted');
    } catch (err) {
      setError((err as Error).message);
      addToast('Schedule submission failed', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirm() {
    setSubmitting(true);
    try {
      const result = await confirmSchedule(
        confirmationId,
        reviewData._csrf,
        reviewData._formId
      );
      setConfirmUrl(result.confirmUrl);
      setStep('confirmed');
      addToast('Schedule confirmed');
    } catch (err) {
      addToast((err as Error).message, 'error');
    } finally {
      setSubmitting(false);
    }
  }

  // Get available times for selected date
  const availableTimes = scheduleData?.availableSlots?.find(
    (s: any) => s.date === scheduledDate
  )?.times || [];

  if (loading) {
    return (
      <><Navbar /><main className="page-container"><p>Loading schedule form...</p></main></>
    );
  }

  if (error && !scheduleData) {
    return (
      <><Navbar /><main className="page-container"><div className="error-message">{error}</div></main></>
    );
  }

  return (
    <>
      <Navbar />
      <main className="page-container">
        <h1>Schedule: {scheduleData?.taskTitle}</h1>

        {/* Step indicator */}
        <div className="step-indicator">
          <span className={step === 'form' ? 'step active' : 'step done'}>1. Schedule</span>
          <span className={step === 'review' ? 'step active' : step === 'confirmed' ? 'step done' : 'step'}>2. Review</span>
          <span className={step === 'confirmed' ? 'step active' : 'step'}>3. Confirmed</span>
        </div>

        {error && <div className="error-message">{error}</div>}

        {/* Step 1: Form */}
        {step === 'form' && (
          <form onSubmit={handleSubmit} className="form-card">
            <input type="hidden" name="_csrf" value={scheduleData?._csrf || ''} />
            <input type="hidden" name="_formId" value={scheduleData?._formId || ''} />

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="scheduledDate">Date *</label>
                <select
                  id="scheduledDate"
                  value={scheduledDate}
                  onChange={(e) => {
                    setScheduledDate(e.target.value);
                    const slot = scheduleData?.availableSlots?.find((s: any) => s.date === e.target.value);
                    if (slot?.times?.[0]) setScheduledTime(slot.times[0]);
                  }}
                  required
                >
                  {scheduleData?.availableSlots?.map((slot: any) => (
                    <option key={slot.date} value={slot.date}>{slot.date}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="scheduledTime">Time *</label>
                <select id="scheduledTime" value={scheduledTime} onChange={(e) => setScheduledTime(e.target.value)} required>
                  {availableTimes.map((t: string) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="department">Department</label>
                <select id="department" value={department} onChange={(e) => setDepartment(e.target.value)}>
                  {scheduleData?.departments?.map((d: string) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="priority">Priority</label>
                <select id="priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>

            {/* Meeting Type — controls conditional fields (Playwright testing target) */}
            <div className="form-group">
              <label htmlFor="meetingType">Meeting Type</label>
              <select
                id="meetingType"
                value={meetingType}
                onChange={(e) => setMeetingType(e.target.value)}
                data-testid="meeting-type-select"
              >
                <option value="standard">Standard</option>
                <option value="video_call">Video Call</option>
                <option value="in_person">In Person</option>
                <option value="workshop">Workshop</option>
              </select>
            </div>

            {/* Conditional fields — shown/hidden based on meetingType */}
            {(meetingType === 'video_call' || meetingType === 'workshop') && (
              <div className="form-row conditional-fields" data-testid="contact-fields">
                <div className="form-group">
                  <label htmlFor="contactName">Contact Name</label>
                  <input id="contactName" type="text" value={contactName} onChange={(e) => setContactName(e.target.value)} />
                </div>
                <div className="form-group">
                  <label htmlFor="contactEmail">Contact Email</label>
                  <input id="contactEmail" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
                </div>
              </div>
            )}

            {meetingType === 'in_person' && (
              <div className="form-row conditional-fields" data-testid="location-fields">
                <div className="form-group">
                  <label htmlFor="location">Location</label>
                  <input id="location" type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Building A" />
                </div>
                <div className="form-group">
                  <label htmlFor="roomNumber">Room Number</label>
                  <input id="roomNumber" type="text" value={roomNumber} onChange={(e) => setRoomNumber(e.target.value)} placeholder="301" />
                </div>
              </div>
            )}

            {meetingType === 'workshop' && (
              <div className="form-row conditional-fields" data-testid="workshop-fields">
                <div className="form-group">
                  <label htmlFor="duration">Duration (minutes)</label>
                  <input id="duration" type="number" value={duration} onChange={(e) => setDuration(e.target.value)} min="15" max="480" />
                </div>
                <div className="form-group">
                  <label htmlFor="participants">Participants (comma-separated)</label>
                  <input id="participants" type="text" value={participants} onChange={(e) => setParticipants(e.target.value)} placeholder="user01, user02" />
                </div>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="notes">Notes</label>
              <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
            </div>

            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Submitting...' : 'Submit Schedule'}
            </button>
          </form>
        )}

        {/* Step 2: Review */}
        {step === 'review' && reviewData && (
          <div className="form-card">
            <h2>Review Your Booking</h2>
            <dl className="detail-list">
              <dt>Confirmation ID</dt><dd>{confirmationId}</dd>
              <dt>Task</dt><dd>{reviewData.task_title || scheduleData?.taskTitle}</dd>
              <dt>Date</dt><dd>{reviewData.slot_date}</dd>
              <dt>Time</dt><dd>{reviewData.slot_time}</dd>
              <dt>Department</dt><dd>{reviewData.department || '—'}</dd>
              <dt>Priority</dt><dd>{reviewData.priority || '—'}</dd>
              <dt>Status</dt><dd><span className="badge badge-pending">{reviewData.status || 'pending'}</span></dd>
            </dl>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
              <button onClick={handleConfirm} className="btn-primary" style={{ width: 'auto' }} disabled={submitting}>
                {submitting ? 'Confirming...' : 'Confirm Booking'}
              </button>
              <button onClick={() => navigate(`/tasks/${taskId}`)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirmed */}
        {step === 'confirmed' && (
          <div className="form-card" data-testid="schedule-confirmed">
            <h2>Booking Confirmed</h2>
            <p>Your schedule has been confirmed.</p>
            {confirmUrl && (
              <p>
                Confirmation link: <code>{confirmUrl}</code>
              </p>
            )}
            <button onClick={() => navigate(`/tasks/${taskId}`)} className="btn-primary" style={{ width: 'auto', marginTop: '1rem' }}>
              Back to Task
            </button>
          </div>
        )}
      </main>
    </>
  );
}
