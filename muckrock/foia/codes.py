"""Status codes for autoimporting documents"""

# pylint: disable=C0301

CODES = {
	'FIX-I': ('Fix Required', 'fix', 'A letter stating that a fix is required, requiring either proof of death or a certificate of authorization from the subject of the request in question.'),
	'ACK': ('Acknowledgement Letter', 'processed', 'An acknowledgement letter, stating the request is being processed.'),
	'NRD': ('No Responsive Documents', 'no_docs', 'A no responsive documents response.'),
	'RES-C': ('Cover Letter', 'processed', 'A cover letter granting the request and outlining any exempted materials, if any.'),
	'RES': ('Responsive Documents', 'done', 'A copy of documents responsive to the request.'),
	'FEE-R': ('Fee Waiver Rejected', 'payment', 'A letter stating the request for reduced or waived fees has been rejected.'),
	'FEE-A': ('Fee Waiver Accepted', 'processed', 'A letter stating the request for reduced or waived fees has been accepted.'),
	'FEE': ('Payment Required', 'payment', 'A letter stating the requester must agree to or prepay assessed or estimated fees in order for the agency to continue processing the request.'),
	'REJ-V': ('Request Rejected', 'rejected', 'The request has been rejected as being too vague, burdensome or otherwise unprocessable.'),
	'REJ-G': ('Glomar Response', 'rejected', 'The request has been rejected, with the agency stating that it can neither confirm nor deny the existence of the requested documents.'),
	'FIX-D': ('Fix Required', 'fix', 'A fix is required to perfect the request. The agency has asked the requester to specify a date range for the requested materials.'),
	'FIX-F': ('Fix Required', 'fix', 'A fix is required to perfect the request. The agency has asked the requester to verify their willingess to pay a fee.'),
	'FIX-V': ('Fix Required', 'fix', 'A fix is required to perfect the request. The request has been rejected as being too vague, burdensome or otherwise unprocessable.'),
	'FWD': ('Request Forwarded', None, 'The request has been forwarded from one agency to another agency or department for further review or follow up.'),
	'INT': ('Interim Response', 'processed', 'An interim response, stating the request is being processed.'),
	'INT-D': ('Interim Response', 'processed', 'An interim response, stating the request has been delayed'),
	'App-Ack': ('Appeal Acknowledgement', 'appealing', 'A letter stating that the request appeal has been received and is being processed.'),
	'App-R': ('Appeal Rejected', 'rejected', 'A letter stating that the request appeal has been rejected.'),
	'App-A': ('Appeal Succesful', 'processed', 'A letter stating that the request appeal has been succesful.'),
}