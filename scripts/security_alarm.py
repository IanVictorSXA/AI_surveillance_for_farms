# Based on Ultralytics: https://github.com/ultralytics/ultralytics/blob/main/ultralytics/solutions/security_alarm.py#L10-L151

import cv2
from queue import Queue
import threading

class SecurityAlarm():
    """A class to manage security alarm functionalities for real-time monitoring.

    This class extends the BaseSolution class and provides features to monitor objects in a frame, send email
    notifications when specific thresholds are exceeded for total detections, and annotate the output frame for
    visualization.

    Attributes:
        records (int): Threshold for the number of detected objects to trigger an alert.
        server (smtplib.SMTP): SMTP server connection for sending email alerts.
        to_email (str): Recipient's email address for alerts.
        from_email (str): Sender's email address for alerts.

    Methods:
        authenticate: Set up email server authentication for sending alerts.
        send_email: Send an email notification with details and an image attachment.
        process: Monitor the frame, process detections, and trigger alerts if thresholds are crossed.

    Examples:
        >>> security = SecurityAlarm()
        >>> security.authenticate("abc@gmail.com", "1111222233334444", "xyz@gmail.com")
        >>> frame = cv2.imread("frame.jpg")
        >>> results = security.process(frame)
    """

    def __init__(self, verbose=False) -> None:
        """Initialize the SecurityAlarm class with parameters for real-time object monitoring.

        Args:
            verbose (bool): Whether to print verbose output.
        """
        self.server = None
        self.to_email = ""
        self.from_email = ""
        self.verbose = verbose

        self.email_queue = Queue()  # Queue to hold email notifications

    def authenticate(self, from_email: str, password: str, to_email: str) -> None:
        """Authenticate the email server for sending alert notifications.

        https://myaccount.google.com/apppasswords

        This method initializes a secure connection with the SMTP server and logs in using the provided credentials.

        Args:
            from_email (str): Sender's email address.
            password (str): Password for the sender's email account.
            to_email (str): Recipient's email address.

        Examples:
            >>> alarm = SecurityAlarm()
            >>> alarm.authenticate("sender@example.com", "password123", "recipient@example.com")
        """
        import smtplib

        self.server = smtplib.SMTP("smtp.gmail.com", 587)
        self.server.starttls()
        self.server.login(from_email, password)
        self.to_email = to_email
        self.from_email = from_email
        threading.Thread(target=self._email_worker, daemon=True).start()  # Start the email worker thread

    def send_email(self, im0, cam_id, date, class_id) -> None:
        self.email_queue.put((im0, cam_id, date, class_id))

    def _send_email_blocking(self, img_bytes, cam_id, date, class_id) -> None:
        """Send an email notification with an image attachment indicating the number of objects detected.

        This method encodes the input image, composes the email message with details about the detection, and sends it
        to the specified recipient.

        Args:
            buffer (bytes): The image buffer to be attached to the email.
            cam_id (str): The ID of the camera that triggered the alert.
            date (str): The date and time of the detection.
            class_id (str): The ID of the detected class.

        Examples:
            >>> alarm = SecurityAlarm()
            >>> frame = cv2.imread("path/to/image.jpg")
            >>> alarm.send_email(frame, records=10)
        """
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText


        # Create the email
        message = MIMEMultipart()
        message["From"] = self.from_email
        message["To"] = self.to_email
        message["Subject"] = "Security Alert"

        # Add the text message body
        message_body = f"Dark Knight Surveillance alert: {class_id} detected at {date} on camera {cam_id}."
        message.attach(MIMEText(message_body))

        # Attach the image
        image_attachment = MIMEImage(img_bytes, name="darkKnight.jpg")
        message.attach(image_attachment)

        # Send the email
        try:
            self.server.send_message(message)
            if self.verbose:
                print("Email sent successfully!")
        except Exception as e:
            if self.verbose:
                print(f"Failed to send email: {e}")

    def _email_worker(self):
        """Worker function to process email notifications from the queue."""
        while True:
            args = self.email_queue.get()

            if args is None:  # Sentinel value to stop the worker
                break

            self._send_email_blocking(*args)
            self.email_queue.task_done()

if __name__ == "__main__":
    sa = SecurityAlarm(verbose=True)
    sender = "ianvictorsouza20@gmail.com"
    receiver = "ianvictorsouza20@gmail.com"
    

    with open("password.txt") as file:
        password = file.readline().strip()

    sa.authenticate(sender, password, receiver)
    
    im = cv2.imread("dark_knight_logo.jpg")
    sa.send_email(im, cam_id="CAM001", date="2023-10-01 12:00:00", class_id="Unknown")